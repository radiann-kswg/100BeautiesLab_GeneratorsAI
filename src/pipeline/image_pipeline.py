"""
pipeline/image_pipeline.py — 画像生成パイプライン オーケストレーター (5 ステージ)
Copyright © RadianN_kswg — CC BY-NC 4.0

ワークフロー:
  Stage 1: コマンド解析 + OpenAI/Gemini でベースプロンプト生成
           (シーン未指定時はキャラクターに合ったシーンをランダム生成)
  Stage 2: キャラクター選定 + 創作 DB から原典画像・特徴を取得
  Stage 3: Gemini Imagen + Adobe 非Firefly でラフ 5 案生成
  Stage 4: OpenAI Vision で違反特徴を分析 + Gemini i2i で修正
  Stage 5: Canva で作風調整・仕上げ → 完成画像 3 枚固定生成

使用方法:
    # キャラクター番号で直接指定 (シーン省略 → ランダム生成)
    python -m src.pipeline.image_pipeline --num 57 --form corefolder

    # シーン指定あり
    python -m src.pipeline.image_pipeline --num 57 --form corefolder \\
        --scene "図書館で本を読んでいるシーン" --skip-canva

    # ★ 自然文で指定 (LLM がキャラクター・シーン等を抽出)
    python -m src.pipeline.image_pipeline \\
        --natural "コアフォルダ姿の25(フィズ)がチョコレートを咥えている絵を生成してほしい"

    # ★ 短編ストーリーファイルから指定
    python -m src.pipeline.image_pipeline --story "_ideas/my_scene.txt"

    # ★ 複数キャラクターを一括生成
    python -m src.pipeline.image_pipeline --nums 25,57 --form corefolder

保存先:
    {OUTPUT_BASE_DIR}/{YYYYMMDD}/{ts}_pipeline_{form}_num{NNN}/   ← 1 実行 = 1 フォルダ
      stage1_prompt/        — 生成済みプロンプト (openai/gemini/base)
      stage2_db/            — DB サマリー + キャラクタースペック
      stage3_rough/         — Adobe 構図ガイド + Gemini Imagen ラフ 5 案
      stage4_correct/       — 違反分析ログ + 修正済み画像
      stage5_final/         — Canva 仕上げ完成画像 3 枚
      pipeline_summary.json — 全ステージの実行結果まとめ

    各ステージ配下の子生成 (Gemini/Canva) は日付フォルダを作らず
    ``{stageN}/{ts}_{provider}_{form}_num{NNN}/`` のようにフラットに配置される
    (旧レイアウトの {YYYYMMDD}/{YYYYMMDD_HH}/ 再ネストは廃止)。

必要な環境変数 (.env):
    GEMINI_API_KEY             — Gemini / Imagen 用
    OPENAI_API_KEY             — GPT-4o 用 (Stage1/4)
    FIREFLY_CLIENT_ID          — Adobe IMS 認証用 (Lightroom/Photoshop API)
    FIREFLY_CLIENT_SECRET      — Adobe IMS 認証用
    ADOBE_STORAGE_TYPE         — "local" (PIL fallback, デフォルト) / "dropbox" / "s3"
    CANVA_ACCESS_TOKEN         — Canva フィニッシング用 (--skip-canva で不要)
    GEMINI_TEXT_MODEL          — Gemini テキストモデル (デフォルト: gemini-2.5-flash)
    GPT_MODEL                  — OpenAI テキストモデル (デフォルト: gpt-4o)
"""

from __future__ import annotations

import argparse
import inspect
import json
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.utils import build_run_output_dir, extract_char_name  # noqa: E402
from src.pipeline.prompt_refiner import refine_prompt_dual, generate_random_scene  # noqa: E402
from src.pipeline.db_collector import collect_character_data  # noqa: E402
from src.utils.dataset import (  # noqa: E402
    IMAGE_TEXT_POLICY, build_appearance_detail_block, normalize_form, record_num, resolve_target,
)
from src.pipeline.design_reference import add_design_reference  # noqa: E402
from src.pipeline.rough_generator import generate_rough_images, retry_rough_images  # noqa: E402
from src.pipeline.correction_generator import check_joint_identity_mixing, correct_rough_images  # noqa: E402
from src.pipeline.final_generator import generate_final_images  # noqa: E402

_ROUGH_COUNT = 5               # Stage 3 (単体): ラフ生成枚数
_MULTI_ROUGH_PER_CHAR = 3     # Stage 3 (合同): キャラクターごとのラフ枚数
_STAGE3_COMP_ROUGH_COUNT = 2   # Stage 3 comp rough: 全体構図ラフ枚数（探索フェーズ）
_STAGE5_SYNTH_COUNT = 2        # Stage 5: 合同の完成画像の上限。構図ラフ 1 枚につき 1 枚（_synth_plans を参照）


def _fmt_num(num: int | str | None) -> str:
    """num を 3 桁表示 or そのまま文字列に変換する。

    int/float のみゼロパディングする: 22 → "022"
    str は型を保持する: "2-alt" → "2-alt"  "000" → "000"
    None は "000" フォールバック（プログラムエラー時の安全網）
    """
    if num is None:
        return "000"
    if isinstance(num, float):
        return f"{int(num):03d}"
    if isinstance(num, int):
        return f"{num:03d}"
    # 文字列 Num はそのまま保持。isdigit() 変換は行わない
    return str(num).strip()


@dataclass
class MultiCharPipelineResult:
    """複数キャラクターを1枚に合同生成するパイプラインの結果。"""
    nums: list[int | str]
    forms: list[str]      # キャラ別形態リスト (nums と同順)
    work_key: str
    pipeline_dir: str
    scene_used: str = ""
    stage1_prompts: dict = field(default_factory=dict)
    stage2_summary: dict = field(default_factory=dict)
    stage3_paths: dict[str, list[str]] = field(default_factory=dict)
    stage4_paths: dict[str, list[str]] = field(default_factory=dict)
    stage5_paths: dict[str, list[str]] = field(default_factory=dict)
    stage5_checks: dict[str, list[str]] = field(default_factory=dict)   # 完成画像ごとの、体数・識別要素の取り違え・配色の指摘
    input_images: list[dict] = field(default_factory=list)   # 依頼者が渡した入力画像の記録 (役割・出所・渡したステージ)
    status: str = "pending"
    errors: list[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0


@dataclass
class PipelineResult:
    num: int | str
    form: str
    work_key: str
    pipeline_dir: str
    scene_used: str = ""
    stage1_prompts: dict = field(default_factory=dict)
    stage2_summary: dict = field(default_factory=dict)
    stage3_paths: dict[str, list[str]] = field(default_factory=dict)
    stage4_paths: dict[str, list[str]] = field(default_factory=dict)
    stage5_paths: dict[str, list[str]] = field(default_factory=dict)
    input_images: list[dict] = field(default_factory=list)   # 依頼者が渡した入力画像の記録 (役割・出所・渡したステージ)
    status: str = "pending"
    errors: list[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0


#: 起点の絵があり、場面も修正指示も無いときに Stage 1 へ渡す場面（ランダムな場面で起点を描き変えない）。
_KEEP_SCENE = "起点の絵の場面・構図・ポーズをそのまま保つ"


def _scene_or_default(scene: str, revisions: "str | list[str] | None", has_start: bool) -> str:
    """場面が未指定のとき、修正指示 → 起点の場面を保つ、の順で補う。どちらも無ければ空（呼び出し側がランダムに決める）。

    i2i は場面なしで修正指示だけを渡すことが多い。修正指示を場面の文脈として渡さないと、「完成形態で」のような
    状態の指示が、RaceType / Height_cm などの曖昧フィールドの解決に届かない。
    """
    if scene:
        return scene
    text = ("; ".join(str(r) for r in revisions if str(r).strip())
            if isinstance(revisions, (list, tuple)) else str(revisions or "")).strip()
    if text:
        print(f"[Stage1] シーン: revisions から補完 ({text[:60]})")
        return text
    if has_start:                   # 赤入れだけ、など。ランダムな場面で起点を描き変えない
        print(f"[Stage1] シーン: {_KEEP_SCENE}")
        return _KEEP_SCENE
    return ""


def _resolve_inputs(
    images: "list[dict] | str | None",
    iterate_from: str | None,
    out_dir: str | None,
    joint: bool = False,
) -> "tuple[list[dict], str | None]":
    """依頼者が渡した入力画像を検証して返す。何も書き出さず、生成 API も呼ばない。

    戻り値は (各ステージへ渡す入力画像, 起点の指定)。赤入れの縦横比を確かめるために改稿の起点を
    取りに行った場合は、起点の指定を手元のパスに置き換えて返す（二度取りに行かない）。
    合同生成で、赤入れだけがあり役割 base の画像が無いときは、改稿の起点を加筆の起点として合成に添える。
    検証に通らなければ ValueError。
    """
    from src.pipeline import input_images

    items = input_images.parse_spec(images)
    if not items:
        return [], iterate_from
    roles = {str(item.get("role") or "") for item in items}
    iterate_base: Path | None = None
    if iterate_from and "markup" in roles and "base" not in roles:
        from src.utils.iterate import resolve_iterate_source
        try:
            iterate_base, _ = resolve_iterate_source(iterate_from)
        except (FileNotFoundError, RuntimeError) as err:
            raise ValueError(f"改稿の起点を読めません: {err}") from err
        iterate_from = str(iterate_base)
        if joint:
            items = [{"role": "base", "path": str(iterate_base), "provenance": "own_generated"}, *items]

    def locate(raw: str) -> Path:
        if iterate_base is not None and raw == str(iterate_base):
            return iterate_base
        return input_images.locate_local(raw, out_dir)

    return input_images.resolve(items, locate=locate, iterate_base=iterate_base, joint=joint), iterate_from


def _prepare_inputs(
    images: "list[dict] | str | None",
    iterate_from: str | None,
    pipeline_dir: Path,
    out_dir: str | None,
    joint: bool = False,
) -> "tuple[list[dict], list[dict], str | None]":
    """入力画像を検証（:func:`_resolve_inputs`）し、実行フォルダーの inputs/ へ書き出す。

    戻り値は (各ステージへ渡す入力画像, 記録用の要約, 起点の指定)。
    """
    from src.pipeline import input_images

    inputs, iterate_from = _resolve_inputs(images, iterate_from, out_dir, joint)
    records = input_images.materialize(inputs, pipeline_dir)
    for record in records:
        print(f"[Pipeline] 入力画像: {record['file']} / 役割 {record['role']} / 出所 {record['provenance']}"
              f" / Stage {','.join(str(s) for s in record['stages'])}")
    return inputs, records, iterate_from


def plan_pipeline(
    nums: "list[int | str]",
    forms: "list[str] | None" = None,
    work_key: str = "#Works_NumberTales",
    *,
    scene: str = "",
    style: str = "",
    composition: str = "",
    background: str = "",
    costume: str = "",
    states: "list[str] | None" = None,
    iterate_from: str | None = None,
    revisions: "str | list[str] | None" = None,
    images: "list[dict] | str | None" = None,
    out_dir: str | None = None,
    quick: bool = False,
    field_overrides: dict[str, str] | None = None,
) -> dict:
    """生成せずに、実行される内容（プロンプトの土台と、役割の付いた画像の一覧）を返す。dry_run が使う。

    課金のある API は呼ばず、出力フォルダーにも何も書かない（GCS の入力画像は検証のために読む）。
    Stage 1 は本番で LLM がプロンプトを加工するので、ここで返すのは加工前の土台。場面が空のときは、
    本番でランダムに決まる。権利のゲートが拒否するキャラクターと、検証に通らない入力は ValueError。
    """
    from src.pipeline import input_images
    from src.utils import apply_generation_gate, find_character
    from src.utils.dataset import (
        build_gemini_prompt, character_selection, collect_reference_images, costume_names,
        describe_ambiguous_field_resolutions, state_names,
    )
    from src.utils.iterate import parse_revisions

    joint = len(nums) > 1
    chosen_forms = list(forms or [])
    chosen_states = list(states or []) + [""] * len(nums)
    _, first_form, work_key = resolve_target(nums[0], chosen_forms[0] if chosen_forms else "corefolder", work_key)
    targets = []
    for index, raw in enumerate(nums):
        form = chosen_forms[index] if index < len(chosen_forms) else first_form
        num, form, _ = resolve_target(raw, form, work_key)
        targets.append((num, form, chosen_states[index]))
    revision_items = parse_revisions(revisions) if isinstance(revisions, str) else list(revisions or [])

    inputs, _ = _resolve_inputs(images, iterate_from, out_dir, joint)      # 本番と同じ検証を通す
    roles = {image["kind"] for image in inputs}
    scene = _scene_or_default(scene, revision_items, bool(iterate_from) or "base" in roles)

    if quick:
        if joint:
            raise ValueError("軽い加筆 (quick) は単体キャラクターだけで使えます。")
        if not iterate_from and "base" not in roles:
            raise ValueError("軽い加筆 (quick) には、起点（iterate_from か、役割 base の画像）が必要です。")
        source: Path | None = None
        if iterate_from and "base" not in roles:
            from src.utils.iterate import resolve_iterate_source

            try:
                source, _ = resolve_iterate_source(iterate_from)
            except (FileNotFoundError, RuntimeError) as err:
                raise ValueError(f"改稿の起点を読めません: {err}") from err
            iterate_from = str(source)
        base, _, _ = input_images.split(inputs, 3)
        with character_selection({(work_key, targets[0][0]): {
            "state": targets[0][2], "costume": costume,
        }}):
            num, form, state = targets[0]
            record = find_character(num, work_key)
            if record is None:
                raise ValueError(f"キャラクター #{num} ({work_key}) が見つかりません。")
            proceed, gate = apply_generation_gate(record, usage="image", num=num)
            if not proceed:
                raise ValueError(f"#{_fmt_num(num)} は生成できません（ai_training opt-out: {gate['reason']}）。")
            overrides = field_overrides or {}
            prompt = _quick_edit_prompt(
                record, form, inputs, revision_items, overrides,
                _previous_base_prompt(source) if source else "", resolve_llm=False,
            )
            references = collect_reference_images(record, form)
            fields = describe_ambiguous_field_resolutions(
                record, form, scene=_KEEP_SCENE, field_overrides=overrides, resolve_llm=False,
            )
            character = {
                "num": num, "form": form, "name": extract_char_name(record, fallback=f"#{_fmt_num(num)}"),
                "ai_training_gate": gate, "state": state, "state_names": state_names(record),
                "costume": costume, "costume_names": costume_names(num, work_key),
                "free_costume_note": "" if costume in costume_names(num, work_key) else costume,
                "base_prompt": prompt, "field_overrides": overrides,
                "field_resolutions": fields,
                "official_references": [Path(p).name for p in references.get("local_paths") or []],
            }
        return {
            "status": "dry_run",
            "message": "生成していません。内容を利用者に示し、承認を得てから dry_run なしで呼んでください。",
            "pipeline": "quick", "work_key": work_key, "scene": _KEEP_SCENE,
            "iterate_from": str(base["path"]) if base and base.get("path") else (str(source) if source else ""),
            "revisions": revision_items,
            "characters": [character], "input_images": [input_images.describe(image) for image in inputs],
            "start_image": input_images.describe(base) if base else {"path": iterate_from},
            "quick_prompt": prompt, "generation_count": 1,
            "notes": ["軽い加筆 (quick): 表示した起点とプロンプトを使い、画像生成を 1 回だけ実行します。",
                      "未指定の曖昧フィールドは候補を表示しています。選択が必要な場合は field_overrides で明示してください。"],
        }

    characters = []
    selection = {(work_key, num): {"state": state, "costume": costume} for num, _, state in targets}
    with character_selection(selection):
        for num, form, state in targets:
            record = find_character(num, work_key)
            if record is None:
                raise ValueError(f"キャラクター #{num} ({work_key}) が見つかりません。")
            proceed, gate = apply_generation_gate(record, usage="image", num=num)
            if not proceed:
                raise ValueError(f"#{_fmt_num(num)} は生成できません（ai_training opt-out: {gate['reason']}）。")
            free_costume = "" if costume in costume_names(num, work_key) else costume
            prompt = build_gemini_prompt(
                record, form, scene="" if joint else scene, style=style, composition=composition,
                background=background, revisions=None if joint else revision_items or None,
                field_overrides=field_overrides, resolve_llm=False)["prompt"]
            block = "" if joint else input_images.prompt_block(
                inputs, 3, has_revisions=bool(revision_items), has_iterate_source=bool(iterate_from) and "base" not in roles)
            if joint:       # 本番でキャラ別のラフに添える「1 体だけ」の指定 (_run_combined_pipeline と同じ)
                prompt = _solo_rough_note(extract_char_name(record, fallback=f"#{_fmt_num(num)}")) + "\n\n" + prompt
            references = collect_reference_images(record, form)
            characters.append({
                "num": num, "form": form, "name": extract_char_name(record, fallback=f"#{_fmt_num(num)}"),
                "ai_training_gate": gate,
                "state": state, "state_names": state_names(record),
                "costume": costume, "costume_names": costume_names(num, work_key),
                "free_costume_note": free_costume,
                "base_prompt": (block + "\n\n" if block else "") + prompt,
                "field_overrides": field_overrides or {},
                "field_resolutions": describe_ambiguous_field_resolutions(
                    record, form, scene=scene, field_overrides=field_overrides, resolve_llm=False,
                ),
                "official_references": [Path(p).name for p in references.get("local_paths") or []],
            })
    joint_block = input_images.prompt_block(inputs, 5, has_revisions=bool(revision_items)) if joint else ""
    return {
        "status": "dry_run",
        "message": "生成していません。内容を利用者に示し、承認を得てから dry_run なしで呼んでください。",
        "pipeline": "joint-five-stage" if joint else "five-stage",
        "work_key": work_key,
        "scene": scene or "（未指定。本番で Stage 1 がランダムに決めます）",
        "iterate_from": iterate_from or "",
        "revisions": revision_items,
        "characters": characters,
        "input_images": [input_images.describe(image) for image in inputs],
        "joint_input_block": joint_block,
        "notes": [
            "base_prompt は Stage 1 の LLM が加工する前の土台です。本番のプロンプトは実行フォルダーの stage1_prompt/ に残ります。",
            "未指定の曖昧フィールドは候補を表示しています。選択が必要な場合は field_overrides で明示してください。",
            "画像生成の回数の目安: 単体はラフ 5・修正 最大 5・合成 3。合同は 1 体につきラフ 3・修正 最大 3、構図ラフ 2（検査に落ちた分は 1 回ずつ描き直すので最大 4）、合成 最大 2（検査を通った構図ラフ 1 枚につき 1）。",
        ],
    }


def _previous_base_prompt(source: Path) -> str:
    """起点の画像が以前のパイプライン実行の中にあれば、その Stage 1 の土台プロンプトを返す（無ければ空文字）。"""
    for parent in Path(source).resolve().parents:
        saved = parent / "stage1_prompt" / "prompt_base_gemini.txt"
        if saved.is_file():
            return saved.read_text(encoding="utf-8").strip()
        if (parent / "pipeline_summary.json").is_file():
            break
    return ""


def _quick_edit_prompt(
    record: dict,
    form: str,
    inputs: list[dict],
    revisions: list[str],
    field_overrides: dict[str, str],
    previous_prompt: str,
    *,
    resolve_llm: bool,
) -> str:
    from src.pipeline import input_images
    from src.utils.dataset import _build_revision_block, build_gemini_prompt

    prompt = previous_prompt or build_gemini_prompt(
        record, form, scene=_KEEP_SCENE, field_overrides=field_overrides,
        resolve_llm=resolve_llm,
    )["prompt"]
    field_block = ""
    if field_overrides:
        field_block = "[明示されたフィールド指定]\n" + "\n".join(
            f"- {name}: {value}" for name, value in field_overrides.items()
        ) + "\n- 上記の値を必ず反映する。"
    blocks = [
        input_images.prompt_block(
            inputs, 3, has_revisions=bool(revisions),
            has_iterate_source=not any(image["kind"] == "base" for image in inputs),
        ),
        _build_revision_block(revisions),
        field_block,
        prompt,
    ]
    return "\n\n".join(block for block in blocks if block)


def run_quick_edit(
    num: int | str,
    form: str = "corefolder",
    work_key: str = "#Works_NumberTales",
    out_dir: str | None = None,
    iterate_from: str | None = None,
    revisions: "str | list[str] | None" = None,
    images: "list[dict] | str | None" = None,
    costume: str = "",
    state: str = "",
    field_overrides: dict[str, str] | None = None,
) -> "PipelineResult":
    """軽い加筆: 起点の絵を 1 回だけ編集し、完成画像 1 枚を新しい実行フォルダー (``_iterN``) に保存する。

    残すのは権利のゲートとプロンプト（起点が以前のパイプライン実行なら、その Stage 1 の土台を使い回す）。
    省くのは Stage 1 の LLM 加工、Stage 2 の観察、Stage 4 の検査、Canva。入力画像は、役割のラベルを
    付けて、この 1 回の編集にすべて渡す。起点（``iterate_from`` か役割 base の画像）が無ければ失敗にする。
    """
    from src.gemini.generate import generate_image
    from src.pipeline import input_images
    from src.utils import apply_generation_gate, find_character
    from src.utils.dataset import build_gemini_prompt, character_selection
    from src.utils.iterate import is_remote_url, next_iteration_label, parse_revisions, resolve_iterate_source

    start_time = datetime.now()
    num, form, work_key = resolve_target(num, form, work_key)
    items = input_images.parse_spec(images)
    has_base = any(item.get("role") == "base" for item in items)
    label_source = Path("inputs") if has_base or not iterate_from or is_remote_url(iterate_from) else Path(iterate_from)
    pipeline_dir = build_run_output_dir(
        provider="pipeline", num=num, form=form, base_dir=out_dir, timestamp=start_time,
        suffix=next_iteration_label(label_source),
    )
    print(f"\n[Pipeline] quick - #{_fmt_num(num)} {form} / out: {pipeline_dir}")
    result = PipelineResult(num=num, form=form, work_key=work_key, pipeline_dir=str(pipeline_dir))

    def _fail(message: str, status: str = "failed") -> PipelineResult:
        result.status = status
        result.errors.append(message)
        _save_summary(pipeline_dir, result, start_time)
        return result

    with character_selection({(work_key, num): {"state": state, "costume": costume}}):
        record = find_character(num, work_key)
        if record is None:
            return _fail(f"キャラクター #{num} ({work_key}) が見つかりません。")
        proceed, gate = apply_generation_gate(record, usage="image", num=num, printer=print)
        if not proceed:
            return _fail(f"ai_training opt-out: {gate['reason']}", "skipped")
        if not iterate_from and not has_base:
            return _fail("軽い加筆 (quick) には、起点（iterate_from か、役割 base の画像）が必要です。")
        try:
            source: Path | None = None
            if iterate_from and not has_base:
                source, _ = resolve_iterate_source(iterate_from)
                iterate_from = str(source)
            inputs, result.input_images, iterate_from = _prepare_inputs(images, iterate_from, pipeline_dir, out_dir)
        except (ValueError, FileNotFoundError, RuntimeError) as err:
            return _fail(f"入力画像: {err}")

        # quick は 1 回の編集に全部の役割を渡す (Stage 3 の振り分けと同じ並び)
        base, leading, trailing = input_images.split(inputs, 3)
        if base:
            iterate_from = str(base["path"])
        revision_items = parse_revisions(revisions) if isinstance(revisions, str) else list(revisions or [])
        reused = _previous_base_prompt(source) if source else ""
        overrides = field_overrides or {}
        prompt = reused or build_gemini_prompt(
            record, form, scene=_KEEP_SCENE, field_overrides=overrides,
        )["prompt"]
        final_prompt = _quick_edit_prompt(
            record, form, inputs, revision_items, overrides, prompt, resolve_llm=True,
        )
        result.scene_used = _KEEP_SCENE
        result.stage1_prompts = {
            "quick": True, "prompt_source": "previous_run" if reused else "base_prompt",
            "iterate_from": iterate_from, "revisions": revision_items, "field_overrides": overrides,
        }
        stage1_dir = pipeline_dir / "stage1_prompt"
        stage1_dir.mkdir(parents=True, exist_ok=True)
        (stage1_dir / "prompt_base_gemini.txt").write_text(prompt, encoding="utf-8")

        print(f"\n[=] quick: 起点の絵を 1 回だけ編集 (修正指示 {len(revision_items)} 件 / 入力画像 {len(inputs)} 枚)")
        try:
            paths = generate_image(
                num=num, form=form, work_key=work_key, out_dir=str(pipeline_dir / "stage5_final"), count=1,
                prompt_override=final_prompt, iterate_from=iterate_from,
                extra_ref_locals=[str(image["path"]) for image in leading] or None,
                trailing_ref_locals=[str(image["path"]) for image in trailing] or None,
                ref_label_overrides=input_images.labels([*([base] if base else []), *leading, *trailing]) or None,
            )
        except SystemExit as err:
            return _fail(f"quick: {err}")
        except Exception as err:  # noqa: BLE001
            return _fail(f"quick: {type(err).__name__}: {err}")
    if not paths:
        return _fail("quick: 画像を生成できませんでした。")
    result.stage5_paths = {"synth": [str(p) for p in paths], "canva": [], "all": [str(p) for p in paths]}
    result.status = "ok"
    _save_summary(pipeline_dir, result, start_time)
    return result


def run_image_pipeline(*args: Any, state: str = "", **kwargs: Any) -> "PipelineResult":
    """状態と衣装の指定を有効にして、単体のパイプライン（:func:`_run_image_pipeline`）を実行する。

    ``state`` と ``costume`` は、DB にある名前（``state_names`` / ``costume_names``）ならその項目を選ぶ。
    名前に当たらない文は、体型と衣装・着用物だけを変える自由な指定になる。ほかの引数は本体と同じ。
    """
    from src.utils.dataset import character_selection, costume_names, find_character

    bound = inspect.signature(_run_image_pipeline).bind(*args, **kwargs)
    bound.apply_defaults()
    params = bound.arguments
    # 指定は、本体が検索に使うのと同じ（作品コード付きのバッジを解決した）番号と作品キーに結び付ける
    num, _, work_key = resolve_target(params["num"], params["form"], params["work_key"])
    with character_selection({(work_key, num): {"state": state, "costume": params["costume"]}}):
        if params["costume"] in costume_names(num, work_key):
            params["costume"] = ""      # DB にある衣装は部位別仕様で描く。自由な衣装差分として LLM へ渡さない
        note = ((find_character(num, work_key) or {}).get("_selection") or {}).get("state_note")
        if note:                        # 自由な文の状態は、値を複数持つ欄（身長など）の選び方にも効かせる
            params["scene"] = "; ".join(filter(None, [params["scene"], f"状態: {note}"]))
        return _run_image_pipeline(*bound.args, **bound.kwargs)


def _run_image_pipeline(
    num: int | str,
    form: str = "corefolder",
    work_key: str = "#Works_NumberTales",
    out_dir: str | None = None,
    scene: str = "",
    style: str = "",
    composition: str = "",
    background: str = "",
    costume: str = "",
    field_overrides: dict[str, str] | None = None,
    skip_canva: bool = False,
    correction_mode: str = "t2i",
    iterate_from: str | None = None,
    revisions: "str | list[str] | None" = None,
    rough_provider: str = "gemini",
    stage_callback: "Callable[[str, dict, str], None] | None" = None,
    reference_confirmation: "Callable[[dict], bool | None] | None" = None,
    images: "list[dict] | str | None" = None,
) -> PipelineResult:
    """画像生成パイプライン全体 (Stage 1→2→3→4→5) を実行する。

    Parameters
    ----------
    num:             キャラクター番号
    form:            形態 ("corefolder" / "humanoid")
    work_key:        作品キー
    out_dir:         出力ベースディレクトリ (None で環境変数 OUTPUT_BASE_DIR)
    scene:           シーン・ポーズ説明 (空の場合は revisions → ランダム生成の順でフォールバック)
    style:           作風ヒント
    composition:     構図ヒント
    background:      背景ヒント
    costume:         衣装差分の説明 (例: '黒いワンピース姿の差分')。空ならデフォルト衣装。
    field_overrides: RaceType 等の曖昧フィールド（複数候補から1つ選ぶ必要があるもの）の
                     明示上書き指定 (例: {"RaceType": "最終的な設計目標"})。
                     未指定フィールドはシーン文脈をもとに LLM が自動判定する。
    skip_canva:      True なら Stage 5 の Canva フィニッシングをスキップ
    correction_mode: 重度違反時の対処モード ("t2i" | "stage3")
                     "t2i"    — Stage 4 内で T2I フル再生成 (デフォルト)
                     "stage3" — Stage 3 に差し戻してラフを再生成
    iterate_from:    前回生成画像のパス (ファイルまたはrun-dir、またはGCS URL)。
                     指定時は Stage 3 が i2i モードになる。Stage 4/5 は通常通り実行。
    revisions:       修正指示 (";"/改行区切り文字列 or list)。iterate_from と組み合わせて使用。
    rough_provider:  Stage 3 のラフ生成プロバイダ ("gemini" | "sdxl" | "both")。
                     "sdxl"/"both" は GCE VM 起動を伴う (課金注意)。既定は "gemini"。
    stage_callback:  ステージ完了時コールバック: (stage_name, stage_paths_dict, pipeline_dir_str) → None。
                     Stage3/4 完了直後に呼ばれ、GCS 中間アップロードや部分結果保存に利用される。
    images:          依頼者が渡す入力画像 [{role, path か object_key, note, provenance}]
                     (役割ごとの枚数と渡すステージは src/pipeline/input_images.py)。
                     役割 base の画像は、iterate_from より優先して加筆の起点になる。

    Returns
    -------
    PipelineResult — 全ステージの実行結果
    """
    start_time = datetime.now()

    num, form, work_key = resolve_target(num, form, work_key)  # バッジ → Num / 他作品は humanoid
    pipeline_dir = build_run_output_dir(
        provider="pipeline",
        num=num,
        form=form,
        base_dir=out_dir,
        timestamp=start_time,
    )
    print(f"\n[Pipeline] start - #{_fmt_num(num)} {form} / out: {pipeline_dir}")
    print(f"[Pipeline] skip_canva={skip_canva}")

    result = PipelineResult(
        num=num, form=form, work_key=work_key,
        pipeline_dir=str(pipeline_dir),
    )
    print(f"[Pipeline] correction_mode={correction_mode}")

    # ──────────────────────────────────────
    # Stage 1: コマンド解析 + プロンプト生成
    # ──────────────────────────────────────
    print("\n[=] Stage 1: プロンプト生成 (OpenAI + Gemini)")
    stage1_dir = pipeline_dir / "stage1_prompt"
    stage1_dir.mkdir(parents=True, exist_ok=True)

    # Stage 2 でレコードを取得するが、ランダムシーン生成には先にレコードが必要。
    # 軽量な find_character を先行呼び出しし、Stage 2 で再利用する。
    from src.utils import apply_generation_gate, find_character
    _pre_record = find_character(num, work_key)
    if _pre_record is None:
        result.status = "failed"
        result.errors.append(f"キャラクター #{num} ({work_key}) が見つかりません。")
        _save_summary(pipeline_dir, result, start_time)
        return result

    # AI 学習/生成オプトアウト・ゲート（権利軸=skip、充填軸=警告のうえ続行）
    _proceed, _ai_gate = apply_generation_gate(
        _pre_record, usage="image", num=num, printer=print
    )
    if not _proceed:
        result.status = "skipped"
        result.errors.append(f"ai_training opt-out: {_ai_gate['reason']}")
        _save_summary(pipeline_dir, result, start_time)
        return result

    # 依頼者が渡した入力画像は、課金の前に検証して実行フォルダーへ書き出す。
    try:
        inputs, result.input_images, iterate_from = _prepare_inputs(images, iterate_from, pipeline_dir, out_dir)
    except ValueError as err:
        result.status = "failed"
        result.errors.append(f"入力画像: {err}")
        _save_summary(pipeline_dir, result, start_time)
        return result
    has_start = bool(iterate_from) or any(image["kind"] == "base" for image in inputs)

    # シーン未指定 → 修正指示、起点の場面を保つ、の順で補い、それでも未指定ならランダム生成
    scene = _scene_or_default(scene, revisions, has_start)
    if not scene:
        scene = generate_random_scene(_pre_record, form) or ""
        if scene:
            print(f"[Stage1] シーン: {scene} (自動生成)")

    prompts = refine_prompt_dual(
        _pre_record, form,
        scene=scene, style=style, composition=composition, background=background,
        costume=costume, field_overrides=field_overrides,
    )
    result.scene_used = scene
    result.stage1_prompts = {
        k: (v if isinstance(v, str) else f"[{len(v)} items]")
        for k, v in prompts.items()
        if k not in ("ref_urls", "ref_locals")
    }
    if iterate_from:
        result.stage1_prompts["iterate_from"] = iterate_from
        result.stage1_prompts["revisions"] = (
            revisions if isinstance(revisions, list)
            else [r for r in (revisions or "").replace(";", "\n").splitlines() if r.strip()]
        )
    _save_stage1(stage1_dir, prompts)
    i2i_label = f" [i2i: {iterate_from}]" if iterate_from else ""
    print(
        f"[Stage1] done - OpenAI: {len(prompts['openai'])}chars / "
        f"Gemini: {len(prompts['gemini'])}chars{i2i_label}"
    )

    # ──────────────────────────────────────
    # Stage 2: キャラクター選定 + DB データ取得
    # ──────────────────────────────────────
    print("\n[=] Stage 2: キャラクター選定 + 創作 DB データ取得")
    char_data = collect_character_data(num, form, pipeline_dir, work_key, reference_confirmation)
    if char_data is None:
        result.status = "failed"
        result.errors.append(f"Stage 2: キャラクター #{num} のデータ取得に失敗しました。")
        _save_summary(pipeline_dir, result, start_time)
        return result

    record = char_data["record"]
    char_spec = char_data["spec"]
    prompts = add_design_reference(prompts, char_spec)
    result.stage2_summary = {
        "char_name": char_spec.get("char_name", ""),
        "ref_url_count": len(char_data["references"]["urls"]),
        "ref_local_count": len(char_data["references"]["local_paths"]),
        "violation_feature_count": len(char_spec["violation_features"]),
    }

    # ──────────────────────────────────────
    # Stage 3: ラフ 5 案生成 (Adobe + Gemini)
    # ──────────────────────────────────────
    stage3_mode = f"i2i ({iterate_from})" if iterate_from else "T2I"
    print(f"\n[=] Stage 3: ラフ {_ROUGH_COUNT} 案生成 (mode={stage3_mode}, provider={rough_provider})")
    rough_results = generate_rough_images(
        record, form, prompts=prompts,
        pipeline_dir=pipeline_dir, count=_ROUGH_COUNT, work_key=work_key,
        scene=scene, background=background, style=style,
        iterate_from=iterate_from, revisions=revisions,
        rough_provider=rough_provider,
        inputs=inputs,
    )
    result.stage3_paths = {k: [str(p) for p in v] for k, v in rough_results.items()}
    if stage_callback:
        try:
            stage_callback("stage3", result.stage3_paths, str(pipeline_dir))
        except Exception as _cb_err:
            print(f"[WARN] stage_callback(stage3) error: {_cb_err}")

    if not rough_results["all"]:
        result.errors.append(
            "Stage 3: ラフ画像が 1 枚も生成できませんでした (Gemini・OpenAI ともに失敗)。"
        )
        result.status = "partial"
        _save_summary(pipeline_dir, result, start_time)
        return result

    # ──────────────────────────────────────
    # Stage 4: 違反特徴の除去 + 構図修正
    # ──────────────────────────────────────
    print("\n[=] Stage 4: 違反特徴の除去 + 構図修正 (OpenAI Vision + Gemini i2i/T2I)")
    corrected_results = correct_rough_images(
        record, form,
        rough_results=rough_results,
        char_spec=char_spec,
        prompts=prompts,
        pipeline_dir=pipeline_dir,
        work_key=work_key,
        correction_mode=correction_mode,
        inputs=inputs,
    )

    # Stage 3 差し戻し処理 (correction_mode == "stage3" の場合)
    needs_regen = corrected_results.get("needs_regen") or []
    if correction_mode == "stage3" and needs_regen:
        print(f"\n[=] Stage 3-Regen: {len(needs_regen)} 枚の差し戻し再生成")
        regen_paths = retry_rough_images(
            record, form,
            prompts=prompts,
            pipeline_dir=pipeline_dir,
            count=len(needs_regen),
            work_key=work_key,
            scene=scene,
        )
        if regen_paths:
            corrected_results["corrected"].extend(regen_paths)
            corrected_results["all"] = (
                corrected_results["corrected"] + corrected_results["passed"]
            )
            corrected_results["regenerated"] = regen_paths
            result.stage3_paths["regen"] = [str(p) for p in regen_paths]
        else:
            print("[WARN] Stage3-Regen: 再生成失敗。元ラフを pass-through に切り替え。")
            corrected_results["passed"].extend(needs_regen)
            corrected_results["all"] = (
                corrected_results["corrected"] + corrected_results["passed"]
            )

    result.stage4_paths = {
        k: [str(p) for p in v]
        for k, v in corrected_results.items()
        if isinstance(v, list)
    }
    if stage_callback:
        try:
            stage_callback("stage4", result.stage4_paths, str(pipeline_dir))
        except Exception as _cb_err:
            print(f"[WARN] stage_callback(stage4) error: {_cb_err}")

    if not corrected_results["all"]:
        result.errors.append("Stage 4: 修正済み画像が 0 枚でした。Stage 5 をスキップします。")
        result.status = "partial"
        _save_summary(pipeline_dir, result, start_time)
        return result

    # ──────────────────────────────────────
    # Stage 5: Canva 作風調整 + 仕上げ (3 枚固定)
    # ──────────────────────────────────────
    print("\n[=] Stage 5: Canva 作風調整 + 完成画像生成 (3 枚固定)")
    final_results = generate_final_images(
        record, form,
        corrected_results=corrected_results,
        pipeline_dir=pipeline_dir,
        work_key=work_key,
        skip_canva=skip_canva,
        prompts=prompts,
        inputs=inputs,
    )
    result.stage5_paths = {k: [str(p) for p in v] for k, v in final_results.items()}

    result.status = (
        "ok" if final_results["all"]
        else "partial" if corrected_results["all"]
        else "failed"
    )
    _save_summary(pipeline_dir, result, start_time)
    return result


def _build_multi_char_composition_prompt(
    records: list[dict],
    forms_map: dict[int | str, str],
    scene: str,
    has_comp_rough: bool = False,
    ref_offset: int = 0,
) -> str:
    """Stage 3 comp rough / Stage 5 合成用: キャラクター単体レンダーをもとに1枚に合成するプロンプトを生成する。
    skip_db_refs=True と組み合わせ、全体はレンダー、部位は明示した公式部位図を参照する。
    forms_map は {キャラ番号: "corefolder" | "humanoid"} のマッピング。
    has_comp_rough=True のとき、参照1 を構図ガイドとして扱い参照2以降をキャラデザインに割り当てる。
    ref_offset は、これらの前に添付する入力画像（加筆の起点・赤入れ・構図参考）の枚数。参照の番号をその分ずらす。
    """
    def _char_label(r: dict) -> str:
        d = r.get("data") or {}
        raw_num = record_num(r)
        return extract_char_name(r, fallback=f"#{_fmt_num(raw_num)}")

    def _joint_art_style_line() -> str:
        # 2026-08-29: ハードコード文字列をやめ、単体生成と同じ作風キーワード
        # (preferred_art_style + style_analysis_summary) を単一ソースから使う。
        from src.utils.dataset import get_art_style_keywords

        keywords = get_art_style_keywords() or [
            "Cute", "Deformed", "Chibi", "Pastel colors", "Simple background",
        ]
        return ", ".join(keywords)

    def _get_num_key(r: dict) -> int | str:
        raw = record_num(r)
        if isinstance(raw, float):
            return int(raw)
        return raw

    form_rules: list[str] = []
    for r in records:
        n = _get_num_key(r)
        char_form = forms_map.get(n, "corefolder")
        label = _char_label(r)
        if char_form == "humanoid":
            form_rules.append(
                f"- {label}: humanoid 形態（人型シルエット）、腕は2本・手は2つ"
            )
        else:
            form_rules.append(
                f"- {label}: corefolder 形態（球体クッション型シルエット）、人型の腕・手・脚・足を描かない"
            )

    # 入力画像を前に添付するときは、作風の基準を完成イラストに限る（入力画像の画風は写さない）
    style_refs = "キャラクターの完成イラスト" if ref_offset else "全参照画像"
    guide_no, first_char_no = 1 + ref_offset, (2 if has_comp_rough else 1) + ref_offset
    # 範囲は必ず明示する。「以降」と書くと、後ろに添付する部位図まで全員のデザインとして読まれる
    design_refs = f"参照{first_char_no}〜{first_char_no + len(records) - 1}"
    if has_comp_rough:
        # 参照1=構図ガイド、参照2以降=各キャラデザイン という役割分担を明示
        char_list = "\n".join(
            f"- 参照{i + first_char_no}: {_char_label(r)} の完成イラスト（キャラクターデザインの正解）"
            for i, r in enumerate(records)
        )
        lines = [
            "[Stage 5 合成 — 構図ラフを採用してキャラクターデザインを反映した完成画像を生成]",
            "添付の参照画像を使い、1 枚の完成イラストを生成してください。",
            "",
            "[参照画像の役割と優先度]",
            f"- 参照{guide_no} (構図ガイド): 全キャラクターの空間配置・サイズ比・ポーズ関係・画角のガイド。",
            "  この画像の構図・レイアウトを最優先で採用してください。",
            char_list,
            "",
            "[合成指示]",
            f"- 参照{guide_no}の構図（各キャラの位置・サイズ比・ポーズ・画角）を忠実に維持する",
            f"- 各キャラクターの外見・色・識別要素は{design_refs}のデザインに忠実に描く",
            "- 全員が画面内に完全に収まること（頭・胴・下半身のいずれもフレームアウト禁止）",
            f"- 作風・線画・塗りスタイルは{style_refs}に揃えること",
        ]
    else:
        char_list = "\n".join(
            f"- 参照{i + first_char_no}: {_char_label(r)} の完成イラスト"
            for i, r in enumerate(records)
        )
        lines = [
            "[マルチキャラクター合成 — 添付レンダーをもとに全員を 1 枚に]",
            "添付の参照画像（各キャラクターの完成イラスト）を参考に、",
            "全員が同じシーンに自然に配置された 1 枚の画像を生成してください。",
            "",
            "[添付参照画像の内訳]",
            char_list,
            "",
            "[合成指示]",
            "- 全員を 1 枚の構図に自然に収める（全員が画面内に完全に収まること）",
            "- 各キャラクターの形態・番号・識別要素を添付参照に忠実に維持する",
            f"- 作風・線画・塗りスタイルは{'キャラクターの完成イラスト' if ref_offset else '添付参照画像'}に揃えること",
        ]

    lines += [
        "",
        "[キャラクター別形態ルール]",
        *form_rules,
        "",
        "[識別要素の持ち主]",
        "- 番号・名前の表記・ラベル・タグ・首輪・紋章・髪飾りなどの識別要素は、持ち主のキャラクターにだけ描く。"
        "ほかのキャラクターへ写さず、原典指定外への重複も増やさない。",
        "- 公式部位図は、ラベルに名前のあるキャラクターだけの部位。そのキャラクターの指定位置にだけ描く。",
        "",
        "[共通作風]",
        _joint_art_style_line(),
        "",
    ]
    if scene:
        lines += [f"[シーン]", f"- {scene}", ""]
    lines.extend(f"[{_char_label(r)} の部位仕様]\n"
                 + build_appearance_detail_block(r, forms_map.get(_get_num_key(r), "corefolder"))
                 for r in records)
    lines.append(IMAGE_TEXT_POLICY)
    return "\n".join(lines)


def _solo_rough_note(name: str) -> str:
    """合同生成の、キャラクターごとのラフに添える指定。"""
    return (
        "[このラフに描く人数]\n"
        f"- {name} 1 体だけを描く。場面にほかのキャラクターが出てきても、このラフには描かない"
        "（全員を 1 枚に描くのは、あとの合成で行う）。同じキャラクターを 2 体描かない。\n"
        f"- {name} の番号・ラベル・タグは原典の指定部位と数を維持し、指定外へ重複を描かない。"
    )


def _joint_ref_labels(
    records: list[dict],
    renders: "list[Path | str]",
    detail_refs: "list[list[str]]",
    guide: "Path | str | None" = None,
) -> dict[str, str]:
    """合同の合成に添付する参照のラベル ({パス: ラベル})。どの参照がどのキャラクターのものかを名前で示す。

    records・renders・detail_refs は同じ順。持ち主の書かれていないレンダーや部位図からは、番号・ラベル・タグが
    別のキャラクターへ写る (2026-11-20 の合同で、バイナの「試用」ラベルがハツカにも付いた)。
    """
    labels: dict[str, str] = {}
    if guide:
        labels[str(guide)] = "構図ガイド: 全員の配置・サイズ比・ポーズの下書き。キャラクターの外見の基準にはしない。"
    owners: dict[str, list[str]] = {}
    for record, render, details in zip(records, renders, detail_refs):
        name = extract_char_name(record, fallback=f"#{_fmt_num(record_num(record))}")
        labels[str(render)] = f"{name} の単体レンダー: {name} だけの姿・作風・配色・識別要素の正典。"
        for path in details:
            owners.setdefault(str(path), []).append(name)
    for path, names in owners.items():
        who = "・".join(dict.fromkeys(names))
        labels[path] = (f"{who} の公式部位図: {Path(path).name} — {who} だけの部位の字形・形状の拡大資料。"
                        "ほかのキャラクターには描かない。全身・構図は単体レンダーを参照。")
    return labels


#: 構図ラフ 1 枚ごとの構図の指示。同じプロンプト・同じ参照で 2 枚描くと、ほぼ同じ構図が 2 枚できる
#: (2026-11-21 の確認で、構図ラフどうしの差が完成画像どうしの差と同じだった)。場面の指定は変えない。
_COMP_ROUGH_VARIANTS = (
    "カメラは正面、目の高さ。全員の全身と周りの様子が入る、引きの構図。",
    "カメラは斜め上から見下ろす。キャラクターに寄った構図。左右の並びは、最初に挙げたキャラクターを画面の右側に置く。",
)


def _comp_rough_variant_note(index: int, composition: str = "") -> str:
    """構図ラフ ``index`` 枚目 (0 始まり) に足す構図の指示。依頼者が構図を指定していれば、寄り引きだけを変える。"""
    if composition.strip():
        hint = (f"依頼の構図: {composition.strip()}。これを守り、"
                + ("全員の全身が入る引きの絵にする。", "キャラクターに寄った絵にする。")[index % 2])
    else:
        hint = _COMP_ROUGH_VARIANTS[index % len(_COMP_ROUGH_VARIANTS)]
    return ("\n\n[この構図ラフの構図]\n"
            f"- {hint}\n"
            "- 場面の指定 (誰が何をしているか、キャラクターどうしの関係) と、識別要素の持ち主は変えない。")


def _checked_guides(comp_rough_paths: list[Path | tuple[Path, int]], joint_cast: list[tuple[dict, str]],
                    renders: list[Path], redraw=None) -> list[Path]:
    """構図ラフのうち、体数と識別要素の持ち主が合っているものを、合成のガイドとして返す。

    2026-11-20 の合同では、顔が 3 つある構図ラフや、札の付け先を取り違えた構図ラフがあった。
    ``redraw`` (構図ラフの番号と指摘を受け、描き直した画像を返す関数) を渡すと、指摘のあった構図ラフを
    1 回だけ描き直し、描き直した絵が検査を通ればガイドにする。検査できなかった構図ラフは描き直さない。
    """
    guides: list[Path] = []
    for index, entry in enumerate(comp_rough_paths):
        if isinstance(entry, tuple):
            candidate, variant = entry
        else:
            candidate, variant = entry, index
        mixing = check_joint_identity_mixing(candidate, joint_cast, renders=renders)
        found = mixing["mixed"]
        if not mixing["skipped"] and not found:
            guides.append(Path(candidate))
            continue
        reason = "検査がスキップされました" if mixing["skipped"] else (' / '.join(found) or "検査失敗")
        print(f"  [Stage5] 構図ラフ {Path(candidate).name} はガイドに使いません: {reason}")
        if mixing["skipped"] or not found or redraw is None:
            continue
        try:
            redrawn = redraw(variant, found)
        except Exception as err:
            print(f"  [WARN] Stage5: 構図ラフ {Path(candidate).name} の描き直しに失敗: {type(err).__name__}: {err}")
            continue
        for retry in redrawn:
            again = check_joint_identity_mixing(retry, joint_cast, renders=renders)
            if not again["skipped"] and not again["mixed"]:
                guides.append(Path(retry))
                print(f"  [Stage5] 描き直した構図ラフ {Path(retry).name} をガイドに使います")
            else:
                print(f"  [Stage5] 描き直した構図ラフ {Path(retry).name} もガイドに使いません: "
                      f"{' / '.join(again['mixed']) or '検査がスキップされました'}")
    return guides


def _synth_plans(guides: list[Path]) -> list[tuple[Path | None, int]]:
    """合同の完成画像を、どのガイドで何枚描くか。

    ガイド 1 枚につき 1 枚。同じガイドで繰り返すと、プロンプトも参照も同じなのでガイドの写しが並ぶ
    (2026-11-21 の確認で、同じガイドから描いた完成 2 枚の差は、色 0.6/255・線 0.1% だった)。
    検査を通ったガイドが無ければ、ガイドなしで上限の枚数を描く (構図は 1 枚ごとに変わる)。
    """
    return [(guide, 1) for guide in guides[:_STAGE5_SYNTH_COUNT]] or [(None, _STAGE5_SYNTH_COUNT)]


def _compose_multi_char(
    base_record: dict,
    form: str,
    char_renders: list[Path],
    composition_prompt: str,
    synth_dir: Path,
    work_key: str,
    count: int = 3,
    detail_refs: list[str] | None = None,
    inputs: list[dict] | None = None,
    has_revisions: bool = False,
    ref_labels: dict[str, str] | None = None,
) -> list[Path]:
    """Stage 5: 各キャラクターの単体完成レンダーを Gemini マルチ参照で 1 枚に合成する。

    全体の姿・構図は char_renders、部位の字形・形状は各キャラの公式 detail_refs を参照する。
    inputs は依頼者が渡した入力画像。合同生成ではここでだけ使う（加筆の起点・赤入れ・構図参考は
    レンダーの前、参考画像は後ろに、役割のラベルを付けて添付する）。
    ref_labels は :func:`_joint_ref_labels` が作る、レンダーと部位図の持ち主を書いたラベル。
    """
    from src.gemini.generate import generate_image
    from src.pipeline import input_images

    synth_dir.mkdir(parents=True, exist_ok=True)
    render_strs = [str(p) for p in char_renders if p.exists()]
    base, leading, trailing = input_images.split(inputs, 5)
    front = [*([base] if base else []), *leading]
    reference_paths = [str(image["path"]) for image in front] + render_strs + list(dict.fromkeys(detail_refs or []))
    input_block = input_images.prompt_block(inputs, 5, has_revisions=has_revisions)
    if input_block:
        composition_prompt = input_block + "\n\n" + composition_prompt
    inter_sleep = float(os.environ.get("GEMINI_IMAGE_SLEEP", "6"))

    results: list[Path] = []
    for i in range(count):
        if i > 0:
            print(f"[Stage5-Compose] レートリミット対策: {inter_sleep:.0f}秒待機 ({i + 1}/{count})...")
            time.sleep(inter_sleep)
        print(f"[Stage5-Compose] ({i + 1}/{count}) キャラクターレンダー {len(render_strs)} 枚から合成中...")
        try:
            paths = generate_image(
                num=record_num(base_record),
                form=form,
                work_key=work_key,
                out_dir=str(synth_dir),
                count=1,
                prompt_override=composition_prompt,
                extra_ref_locals=reference_paths,
                extra_ref_label="キャラクター単体レンダー: このキャラの姿・作風・配色の正典。",
                trailing_ref_locals=[str(image["path"]) for image in trailing] or None,
                ref_label_overrides={**(ref_labels or {}), **input_images.labels([*front, *trailing])} or None,
                skip_db_refs=True,  # 先頭キャラだけの DB 全体図は混ぜず、各キャラの部位図を明示添付
            )
            results.extend(paths)
        except SystemExit as err:
            print(f"[WARN] Stage5-Compose ({i + 1}): {err}")
        except Exception as err:
            print(f"[WARN] Stage5-Compose ({i + 1}): {type(err).__name__}: {err}")
    return results


def _append_revision_instructions(prompt: str, revisions: "str | list[str] | None") -> str:
    if not revisions:
        return prompt
    from src.utils.dataset import _build_revision_block
    from src.utils.iterate import parse_revisions

    items = parse_revisions(revisions) if isinstance(revisions, str) else list(revisions)
    block = _build_revision_block(items)
    return f"{prompt}\n\n{block}" if block else prompt


def run_combined_pipeline(*args: Any, states: "list[str] | None" = None, **kwargs: Any) -> "MultiCharPipelineResult":
    """状態と衣装の指定を有効にして、合同のパイプライン（:func:`_run_combined_pipeline`）を実行する。

    ``states`` は ``nums`` と同じ順の、キャラクターごとの状態（空文字は既定）。``costume`` は全員に共通。
    """
    from src.utils.dataset import character_selection, costume_names

    bound = inspect.signature(_run_combined_pipeline).bind(*args, **kwargs)
    bound.apply_defaults()
    params = bound.arguments
    # 指定は、本体と同じ規則（先頭のバッジが作品を決める）で解決した番号と作品キーに結び付ける
    _, form, work_key = resolve_target(params["nums"][0], params["form"], params["work_key"])
    nums = [resolve_target(n, form, work_key)[0] for n in params["nums"]]
    chosen = list(states or [])
    if len(chosen) > len(nums):
        raise ValueError("states の件数が nums のキャラクター数より多くなっています。")
    chosen += [""] * (len(nums) - len(chosen))
    selection = {(work_key, num): {"state": state, "costume": params["costume"]} for num, state in zip(nums, chosen)}
    with character_selection(selection):
        if any(params["costume"] in costume_names(num, work_key) for num in nums):
            params["costume"] = ""      # DB にある衣装は部位別仕様で描く。自由な衣装差分として LLM へ渡さない
        return _run_combined_pipeline(*bound.args, **bound.kwargs)


def _run_combined_pipeline(
    nums: list[int | str],
    form: str = "corefolder",
    forms: "list[str] | None" = None,
    work_key: str = "#Works_NumberTales",
    out_dir: str | None = None,
    scene: str = "",
    style: str = "",
    composition: str = "",
    background: str = "",
    costume: str = "",
    field_overrides: dict[str, str] | None = None,
    skip_canva: bool = False,
    correction_mode: str = "t2i",
    iterate_from: str | None = None,
    revisions: "str | list[str] | None" = None,
    stage_callback: "Callable[[str, dict, str], None] | None" = None,
    reference_confirmation: "Callable[[dict], bool | None] | None" = None,
    images: "list[dict] | str | None" = None,
) -> MultiCharPipelineResult:
    """複数キャラクターを 1 枚に合同生成するパイプライン (Stage 1→2→3→4→5)。

    Stage 3-4 はキャラクターごとに個別生成・違反修正を行い、
    Stage 5 で各キャラクターの完成レンダーを Gemini マルチ参照で 1 枚に合成する。

    Parameters
    ----------
    nums:            キャラクター番号リスト (2 件以上)
    form:            全キャラ共通の形態 (forms 未指定時のフォールバック)
    forms:           キャラ別形態リスト (nums と同順)。指定時は form より優先。
                     長さが nums より短い場合は末尾を form で補完する。
                     例: nums=[X, 20], forms=["corefolder", "humanoid"] で
                     Xをコアフォルダ・ハツカをヒューマノイドにして1枚合成できる。
    work_key:        作品キー
    out_dir:         出力ベースディレクトリ
    scene:           シーン (空の場合は先頭キャラから自動生成)
    skip_canva:      True なら Stage 5 Canva をスキップ
    correction_mode: Stage 4 重度違反時の対処モード ("t2i" | "stage3")
    images:          依頼者が渡す入力画像 (src/pipeline/input_images.py)。合同生成では、キャラクターごとの
                     ラフと検査には渡さず、全員を 1 枚にまとめる Stage 5 でだけ使う。

    出力ディレクトリ構成
    --------------------
    pipeline_dir/
      stage1_prompt/           — 統合プロンプト
      char_NNN/stage3_rough/   — キャラクターごとのラフ (各 _MULTI_ROUGH_PER_CHAR 枚)
      char_NNN/stage2_db/      — キャラクターごとの DB サマリー
      char_NNN/stage4_correct/ — キャラクターごとの違反修正結果
      stage3_comp_rough/       — 全キャラ構図ラフ (Stage3 と同時に _STAGE3_COMP_ROUGH_COUNT 枚, 探索)
      stage5_final/            — 全キャラ合成完成画像。検査を通った構図ラフ 1 枚につき 1 枚、最大 _STAGE5_SYNTH_COUNT 枚 (仕上げ)

    Returns
    -------
    MultiCharPipelineResult
    """
    from src.utils import apply_generation_gate, find_character
    from src.gemini.generate import generate_image

    # 先頭のバッジが作品コード付きなら作品を決め、全員を同じ作品の Num / 形態へ揃える。
    _, form, work_key = resolve_target(nums[0], form, work_key)
    nums = [resolve_target(n, form, work_key)[0] for n in nums]
    forms = [normalize_form(str(f).strip().lower() or form, work_key) for f in forms] if forms else forms

    # キャラ別形態マップを構築する。forms が指定されていればそれを優先し、
    # 不足分は form で補完する。
    _resolved_forms: list[str] = []
    for i in range(len(nums)):
        if forms and i < len(forms):
            _resolved_forms.append(str(forms[i]).strip().lower() or form)
        else:
            _resolved_forms.append(form)
    forms_map: dict[int | str, str] = {n: _resolved_forms[i] for i, n in enumerate(nums)}

    start_time = datetime.now()
    primary_form = _resolved_forms[0]
    pipeline_dir = build_run_output_dir(
        provider="pipeline",
        num=nums[0],
        form=primary_form,
        base_dir=out_dir,
        timestamp=start_time,
        nums=nums,
    )
    nums_label = "+".join(f"#{_fmt_num(n)}" for n in nums)
    forms_label = "+".join(_resolved_forms)
    print(f"\n[CombinedPipeline] start - {nums_label} ({forms_label}) → 1 枚合同生成 / out: {pipeline_dir}")
    print(f"[CombinedPipeline] skip_canva={skip_canva} / correction_mode={correction_mode}")

    result = MultiCharPipelineResult(
        nums=nums, forms=_resolved_forms, work_key=work_key,
        pipeline_dir=str(pipeline_dir),
    )

    # 依頼者が渡した入力画像は、課金の前に検証して実行フォルダーへ書き出す。
    try:
        inputs, result.input_images, iterate_from = _prepare_inputs(
            images, iterate_from, pipeline_dir, out_dir, joint=True)
    except ValueError as err:
        result.status = "failed"
        result.errors.append(f"入力画像: {err}")
        _save_summary(pipeline_dir, result, start_time)
        return result
    has_start = bool(iterate_from) or any(image["kind"] == "base" for image in inputs)

    # ── Stage 2: 全キャラクターのレコード + スペック収集 ──
    print(f"\n[=] Stage 2: {len(nums)} キャラクターのレコード + DB データ収集")
    records: list[dict] = []
    char_data_map: dict[int | str, dict] = {}
    for n in nums:
        rec = find_character(n, work_key)
        if rec is None:
            result.status = "failed"
            result.errors.append(f"キャラクター #{n} ({work_key}) が見つかりません。")
            _save_summary(pipeline_dir, result, start_time)
            return result
        # AI 学習/生成オプトアウト・ゲート。合同絵は部分生成できないため、
        # 1 人でも権利軸オプトアウトなら合同全体を中止。充填軸は警告のうえ続行。
        _proceed, _ai_gate = apply_generation_gate(rec, usage="image", num=n, printer=print)
        if not _proceed:
            result.status = "skipped"
            result.errors.append(f"ai_training opt-out (#{_fmt_num(n)}): {_ai_gate['reason']}")
            _save_summary(pipeline_dir, result, start_time)
            return result
        records.append(rec)
        char_dir = pipeline_dir / f"char_{_fmt_num(n)}"
        char_data = collect_character_data(n, forms_map[n], char_dir, work_key, reference_confirmation)
        if char_data is None:
            result.status = "failed"
            result.errors.append(f"Stage 2: #{n} DB データ取得に失敗しました。")
            _save_summary(pipeline_dir, result, start_time)
            return result
        char_data_map[n] = char_data
        print(f"  [Stage2] #{_fmt_num(n)} {extract_char_name(rec, fallback='')} ({forms_map[n]}) — OK")

    result.stage2_summary = {
        "char_names": [extract_char_name(r, fallback="") for r in records],
        "num_chars": len(records),
    }

    # ── Stage 1: シーン補完 + キャラクターごとのプロンプト生成 ──
    print("\n[=] Stage 1: シーン補完 + キャラクターごとのプロンプト生成")
    scene = _scene_or_default(scene, revisions, has_start)
    if not scene:
        scene = generate_random_scene(records[0], forms_map[nums[0]]) or ""
        if scene:
            print(f"[Stage1] シーン: {scene} (先頭キャラから自動生成)")

    per_char_prompts: dict[int, dict] = {}
    for rec in records:
        n = record_num(rec)
        prompts = refine_prompt_dual(
            rec, forms_map[n], scene=scene, style=style,
            composition=composition, background=background,
            costume=costume, field_overrides=field_overrides,
        )
        prompts = add_design_reference(prompts, char_data_map[n]["spec"])
        # 場面は全員で共有する (「寄り添って寝る」など)。1 体ずつのラフにそのまま渡すと、ラフに 2 体描かれて
        # 番号やラベルが取り違えられる。ラフと、その修正・描き直しには「1 体だけ」を明示する。
        solo = _solo_rough_note(extract_char_name(rec, fallback=f"#{_fmt_num(n)}"))
        for key in ("base_gemini", "gemini"):
            if prompts.get(key):
                prompts[key] = solo + "\n\n" + prompts[key]
        per_char_prompts[n] = prompts

    result.scene_used = scene
    result.stage1_prompts = {
        "scene": scene,
        "char_count": len(records),
        "char_names": [extract_char_name(r, fallback="") for r in records],
    }
    if iterate_from:
        result.stage1_prompts["iterate_from"] = iterate_from
        result.stage1_prompts["revisions"] = (
            revisions if isinstance(revisions, list)
            else [r for r in (revisions or "").replace(";", "\n").splitlines() if r.strip()]
        )
    stage1_dir = pipeline_dir / "stage1_prompt"
    stage1_dir.mkdir(parents=True, exist_ok=True)
    for rec in records:
        n = record_num(rec)
        char_stage1_dir = stage1_dir / f"char_{_fmt_num(n)}"
        char_stage1_dir.mkdir(parents=True, exist_ok=True)
        _save_stage1(char_stage1_dir, per_char_prompts[n])
    print(f"[Stage1] done - {len(records)} キャラクター分のプロンプト生成完了")

    # ── Stage 3: キャラクターごとに個別ラフ生成 (_MULTI_ROUGH_PER_CHAR 枚) ──
    stage3_mode = f"i2i ({iterate_from})" if iterate_from else "T2I"
    print(
        f"\n[=] Stage 3: キャラクターごとに個別ラフ生成"
        f" ({_MULTI_ROUGH_PER_CHAR} 枚/キャラ, 計 {len(nums) * _MULTI_ROUGH_PER_CHAR} 枚"
        f", mode={stage3_mode})"
    )
    # revision block は per-char の base_prompt 先頭に共通で差し込む
    _rev_block: str = ""
    if iterate_from and revisions:
        from src.utils.iterate import parse_revisions
        from src.utils.dataset import _build_revision_block
        _rev_items = (
            parse_revisions(revisions) if isinstance(revisions, str) else list(revisions)
        )
        _rev_block = _build_revision_block(_rev_items)

    per_char_roughs: dict[int | str, list[Path]] = {}
    inter_char_sleep = float(os.environ.get("GEMINI_INTER_CHAR_SLEEP", "30"))

    for i, rec in enumerate(records):
        n = record_num(rec)
        if isinstance(n, float):
            n = int(n)
        if i > 0:
            # 直前キャラクターの生成直後にスタートするとレートリミットで失敗するため待機する
            print(f"  [Stage3] キャラクター切り替え待機: {inter_char_sleep:.0f}秒...")
            time.sleep(inter_char_sleep)

        rough_dir = pipeline_dir / f"char_{_fmt_num(n)}" / "stage3_rough"
        rough_dir.mkdir(parents=True, exist_ok=True)
        base_prompt = (per_char_prompts[n].get("base_gemini", "")
                       or per_char_prompts[n].get("gemini", ""))
        if _rev_block and base_prompt:
            base_prompt = _rev_block + "\n\n" + base_prompt
        char_form = forms_map[n]
        print(f"  [Stage3] #{_fmt_num(n)} ({char_form}) ラフ {_MULTI_ROUGH_PER_CHAR} 枚生成中...")
        try:
            paths = generate_image(
                num=n, form=char_form, work_key=work_key,
                out_dir=str(rough_dir),
                count=_MULTI_ROUGH_PER_CHAR,
                prompt_override=base_prompt,
                skip_ref_urls=True,  # DB URL を Gemini サーバーが取得できないケースを回避
                iterate_from=iterate_from,  # 指定時は前回合成画像を参照先頭に差し込む
            )
        except (SystemExit, Exception) as err:
            paths = []
            result.errors.append(f"Stage 3 char#{n}: {err}")
        per_char_roughs[n] = paths
        if not paths:
            result.errors.append(
                f"Stage 3 char#{n}: ラフ 0 枚 — API エラーまたはレートリミットの可能性"
            )
        print(f"  [Stage3] #{_fmt_num(n)} — {len(paths)} 枚生成完了")

    all_stage3 = [p for paths in per_char_roughs.values() for p in paths]
    result.stage3_paths = {
        f"char_{_fmt_num(n)}": [str(p) for p in per_char_roughs.get(n, [])] for n in nums
    }
    result.stage3_paths["all"] = [str(p) for p in all_stage3]
    print(f"[Stage3] done - 合計 {len(all_stage3)} 枚")

    # ── Stage 3 終了時コールバック（comp rough が確定する前の中間通知） ──
    if stage_callback and all_stage3:
        try:
            stage_callback("stage3", result.stage3_paths, str(pipeline_dir))
        except Exception as _cb_err:
            print(f"[WARN] stage_callback(stage3) error: {_cb_err}")

    # ── Stage 3 続き: 全キャラクターが揃う構図ラフを 1 枚同時生成 ──
    # 単体ラフとは別に全員が同じシーンに収まる構図を先行確認するためのラフ。
    # Stage 5 最終合成の前段として i2i の起点にも使える。
    # 全員の単体ラフが 1 枚以上揃っている場合のみ実行する。
    comp_rough_entries: list[tuple[Path, int]] = []
    comp_rough_paths: list[Path] = []
    all_have_rough = all(bool(per_char_roughs.get(n)) for n in nums)
    if all_have_rough:
        print(f"\n  [Stage3-CompRough] 全キャラ構図ラフを同時生成 ({_STAGE3_COMP_ROUGH_COUNT} 枚, 探索)...")
        time.sleep(inter_char_sleep)  # レートリミット対策
        comp_rough_dir = pipeline_dir / "stage3_comp_rough"
        comp_rough_dir.mkdir(parents=True, exist_ok=True)
        comp_ref_images = [per_char_roughs[n][0] for n in nums]
        comp_rough_prompt = _build_multi_char_composition_prompt(records, forms_map, scene)
        try:
            for variant in range(_STAGE3_COMP_ROUGH_COUNT):     # 1 枚ずつ、別の構図の指示を足して描く
                if variant:
                    time.sleep(float(os.environ.get("GEMINI_IMAGE_SLEEP", "6")))   # レートリミット対策
                generated = _compose_multi_char(
                    records[0], primary_form,
                    char_renders=comp_ref_images,
                    composition_prompt=comp_rough_prompt + _comp_rough_variant_note(variant, composition),
                    synth_dir=comp_rough_dir,
                    work_key=work_key,
                    count=1,
                    detail_refs=[p for n in nums for p in char_data_map[n]["spec"].get("detail_reference_paths", [])],
                    ref_labels=_joint_ref_labels(
                        records, comp_ref_images,
                        [char_data_map[n]["spec"].get("detail_reference_paths", []) for n in nums]),
                )
                comp_rough_entries.extend((path, variant) for path in generated)
                comp_rough_paths.extend(generated)
            print(f"  [Stage3-CompRough] {len(comp_rough_entries)} 枚生成完了")
        except Exception as err:
            print(f"  [WARN] Stage3-CompRough: {type(err).__name__}: {err}")
    else:
        print(f"\n  [Stage3-CompRough] 一部キャラのラフが未生成のためスキップ")
    result.stage3_paths["composition_rough"] = [str(p) for p in comp_rough_paths]

    # マルチキャラ合成には全キャラのラフが必要。1 人でも欠けたら中断する。
    failed_chars = [n for n in nums if not per_char_roughs.get(n)]
    if failed_chars:
        failed_label = " / ".join(f"#{_fmt_num(n)}" for n in failed_chars)
        result.errors.append(
            f"Stage 3: {failed_label} のラフ生成に失敗しました。"
            " 全キャラクターのラフが揃わないと合同合成ができません。"
        )
        result.status = "partial"
        _save_summary(pipeline_dir, result, start_time)
        return result

    # ── Stage 4: キャラクターごとに個別違反修正 ──
    print(f"\n[=] Stage 4: キャラクターごとに違反修正 (OpenAI Vision + Gemini i2i/T2I)")
    per_char_best: list[Path] = []  # Stage 5 に渡す各キャラのベスト 1 枚
    per_char_inspected: list[Path | None] = []  # 配色検査用。キャラクター順に合格画像だけを対応付ける
    all_stage4_paths: dict[str, list[str]] = {}

    for rec in records:
        n = record_num(rec)
        if isinstance(n, float):
            n = int(n)
        rough_paths = per_char_roughs.get(n) or []
        if not rough_paths:
            print(f"  [Stage4] #{_fmt_num(n)}: ラフなしのためスキップ")
            continue

        char_dir = pipeline_dir / f"char_{_fmt_num(n)}"
        rough_results = {"gemini": rough_paths, "adobe_guide": [], "all": rough_paths}
        corrected = correct_rough_images(
            rec, forms_map[n],
            rough_results=rough_results,
            char_spec=char_data_map[n]["spec"],
            prompts=per_char_prompts[n],
            pipeline_dir=char_dir,
            work_key=work_key,
            correction_mode=correction_mode,
        )
        all_stage4_paths[f"char_{_fmt_num(n)}"] = [str(p) for p in corrected.get("all") or []]

        # ベスト 1 枚: 違反なし通過画像を優先、なければ修正済みの先頭
        best = (corrected.get("passed") or [])[:1] or (corrected.get("corrected") or [])[:1]
        if best:
            per_char_best.extend(best)
            print(f"  [Stage4] #{_fmt_num(n)}: ベスト 1 枚選定 → {best[0].name}")
        else:
            # 修正も通過もなければ元ラフの先頭をフォールバック
            per_char_best.extend(rough_paths[:1])
            print(f"  [Stage4] #{_fmt_num(n)}: フォールバック → {rough_paths[0].name}")
        inspected = (corrected.get("inspected_passed") or [])[:1]
        per_char_inspected.extend(inspected or [None])

    result.stage4_paths = all_stage4_paths
    result.stage4_paths["best_per_char"] = [str(p) for p in per_char_best]
    print(f"[Stage4] done - 合成用ベスト: {len(per_char_best)} 枚 ({', '.join(p.name for p in per_char_best)})")
    if stage_callback:
        try:
            stage_callback("stage4", result.stage4_paths, str(pipeline_dir))
        except Exception as _cb_err:
            print(f"[WARN] stage_callback(stage4) error: {_cb_err}")

    # ── Stage 5: ベストレンダーを Gemini マルチ参照で 1 枚に合成 ──
    # 検査を通った構図ラフを先頭参照として差し込み、構図ガイドとして Gemini に渡す。完成はガイド 1 枚につき 1 枚。
    joint_cast = [(rec, forms_map[n]) for rec, n in zip(records, nums)]

    def _redraw_comp_rough(variant: int, found: list[str]) -> list[Path]:
        # 検査に落ちた構図ラフを、同じ構図の指示のまま、指摘を添えて 1 回だけ描き直す。
        # 2026-11-21 の確認で、構図ラフ 2 枚のうち 1 枚が落ち、完成が 1 枚だけになった
        time.sleep(float(os.environ.get("GEMINI_IMAGE_SLEEP", "6")))   # レートリミット対策
        details = [char_data_map[n]["spec"].get("detail_reference_paths", []) for n in nums]
        redrawn = _compose_multi_char(
            records[0], primary_form,
            char_renders=per_char_best,
            composition_prompt=(
                _build_multi_char_composition_prompt(records, forms_map, scene)
                + _comp_rough_variant_note(variant, composition)
                + "\n\n[前回の構図ラフで見つかった問題 (解消して描き直す)]\n" + "\n".join(f"- {item}" for item in found)),
            synth_dir=pipeline_dir / "stage3_comp_rough",
            work_key=work_key,
            count=1,
            detail_refs=[p for group in details for p in group],
            ref_labels=_joint_ref_labels(records, per_char_best, details),
        )
        result.stage3_paths["composition_rough"] += [str(p) for p in redrawn]
        return redrawn

    guides = _checked_guides(comp_rough_entries, joint_cast, per_char_inspected, redraw=_redraw_comp_rough)
    plans = _synth_plans(guides)
    result.stage3_paths["composition_guide"] = [str(guide) for guide, _ in plans if guide]
    _comp_note = f" + 構図ラフ参照 {len(guides)} 枚" if guides else "（構図ラフ参照なし）"
    print(f"\n[=] Stage 5: キャラクター完成レンダー {len(per_char_best)} 枚を合成 "
          f"({sum(count for _, count in plans)} 枚, 仕上げ){_comp_note}")
    from src.pipeline import input_images as _input_images
    from src.pipeline.design_reference import design_reference_block
    stage5_dir = pipeline_dir / "stage5_final"
    synth_images: list[Path] = []
    for plan_index, (guide, synth_count) in enumerate(plans):
        if plan_index:
            time.sleep(float(os.environ.get("GEMINI_IMAGE_SLEEP", "6")))   # レートリミット対策 (同じガイドの中は合成側で待つ)
        composition_prompt = _build_multi_char_composition_prompt(
            records, forms_map, scene, has_comp_rough=guide is not None,
            ref_offset=sum(1 for image in _input_images.for_stage(inputs, 5) if image["kind"] != "reference"),
        )
        composition_prompt += "\n".join(
            design_reference_block(char_data_map[n]["spec"]["design_reference"]) for n in nums
        )
        composition_prompt = _append_revision_instructions(composition_prompt, revisions)
        synth_images += _compose_multi_char(
            records[0], primary_form,
            char_renders=([guide] if guide else []) + per_char_best,
            composition_prompt=composition_prompt,
            synth_dir=stage5_dir / "synth",
            work_key=work_key,
            count=synth_count,
            detail_refs=[p for n in nums for p in char_data_map[n]["spec"].get("detail_reference_paths", [])],
            inputs=inputs,
            has_revisions=bool(revisions),
            ref_labels=_joint_ref_labels(
                records, per_char_best,
                [char_data_map[n]["spec"].get("detail_reference_paths", []) for n in nums],
                guide=guide),
        )
    print(f"[Stage5] done - {len(synth_images)} 枚合成完了")

    # 1 体ずつの検査 (Stage 4) では見つけられない、キャラクターどうしの識別要素の取り違えを見る。
    # 直しはせず、pipeline_summary.json に残して依頼者に見せる。
    for image in synth_images:
        mixing = check_joint_identity_mixing(image, joint_cast, renders=per_char_inspected)
        if mixing["mixed"]:
            try:
                image_key = str(image.resolve().relative_to(pipeline_dir.resolve()))
            except ValueError:
                image_key = str(image)
            result.stage5_checks[image_key] = mixing["mixed"]
            print(f"[WARN] Stage5: {image_key} の検査で指摘がありました: {' / '.join(mixing['mixed'])}")

    result.stage5_paths = {
        "synth": [str(p) for p in synth_images],
        "canva": [],
        "all": [str(p) for p in synth_images],
    }
    result.status = (
        "ok" if synth_images
        else "partial" if all_stage3
        else "failed"
    )
    _save_summary(pipeline_dir, result, start_time)
    print(f"\n[CombinedPipeline] done - {nums_label} / status={result.status}")
    return result


def run_multi_pipeline(
    char_params: list[dict],
    out_dir: str | None = None,
    skip_canva: bool = False,
    correction_mode: str = "t2i",
) -> list[PipelineResult]:
    """複数キャラクターのパイプラインをキャラクターごとに順番に実行する。

    Parameters
    ----------
    char_params:     [{"num":int, "form":str, "scene":str, ...}, ...]
    out_dir:         出力ベースディレクトリ
    skip_canva:      True なら Stage 5 Canva をスキップ
    correction_mode: 重度違反時の対処モード ("t2i" | "stage3")

    Returns
    -------
    各キャラクターの PipelineResult のリスト
    """
    results: list[PipelineResult] = []
    print(f"\n[MultiPipeline] {len(char_params)} キャラクターを順番に生成します")

    for i, cp in enumerate(char_params, 1):
        print(f"\n{'=' * 60}")
        print(f"[MultiPipeline] {i}/{len(char_params)}: #{_fmt_num(cp['num'])} / {cp['form']}")
        print(f"{'=' * 60}")
        result = run_image_pipeline(
            num=cp["num"],
            state=cp.get("state", ""),
            form=cp.get("form", "corefolder"),
            work_key=cp.get("work_key", "#Works_NumberTales"),
            out_dir=out_dir,
            scene=cp.get("scene", ""),
            style=cp.get("style", ""),
            composition=cp.get("composition", ""),
            background=cp.get("background", ""),
            skip_canva=skip_canva,
            correction_mode=correction_mode,
        )
        results.append(result)

    ok_count = sum(1 for r in results if r.status == "ok")
    print(f"\n[MultiPipeline] 完了: {ok_count}/{len(results)} 成功")
    return results


# ──────────────────────────────────────────
# 内部ユーティリティ
# ──────────────────────────────────────────

def _save_stage1(stage1_dir: Path, prompts: dict) -> None:
    (stage1_dir / "prompt_openai.txt").write_text(
        prompts.get("openai", ""), encoding="utf-8"
    )
    (stage1_dir / "prompt_gemini.txt").write_text(
        prompts.get("gemini", ""), encoding="utf-8"
    )
    (stage1_dir / "prompt_base_dalle.txt").write_text(
        prompts.get("base_dalle", ""), encoding="utf-8"
    )
    # 軽い加筆 (quick) が使い回す、Stage 3 のラフと Stage 5 の合成に渡した土台
    (stage1_dir / "prompt_base_gemini.txt").write_text(
        prompts.get("base_gemini", "") or prompts.get("gemini", ""), encoding="utf-8"
    )
    meta = {
        "openai_length": len(prompts.get("openai") or ""),
        "gemini_length": len(prompts.get("gemini") or ""),
        "ref_url_count": len(prompts.get("ref_urls") or []),
        "ref_local_count": len(prompts.get("ref_locals") or []),
        "field_overrides": prompts.get("field_overrides") or {},
        "field_resolutions": prompts.get("field_resolutions") or {},
    }
    (stage1_dir / "stage1_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _save_summary(
    pipeline_dir: Path,
    result: "PipelineResult | MultiCharPipelineResult",
    start_time: datetime,
) -> None:
    elapsed = (datetime.now() - start_time).total_seconds()
    result.elapsed_seconds = round(elapsed, 1)
    (pipeline_dir / "pipeline_summary.json").write_text(
        json.dumps(asdict(result), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n[Pipeline] done - status={result.status} / elapsed: {elapsed:.1f}s")
    print(f"[Pipeline] 出力先: {pipeline_dir}")


# ──────────────────────────────────────────
# CLI エントリポイント
# ──────────────────────────────────────────

def _resolve_num_arg(raw: str) -> int | str:
    """--badge / --nums 引数をキャラクター ID に変換する。
    "57" → 57  "2B" → "2-alt"  "2-alt" → "2-alt"  "バイナ" → "2-alt"  "フジ" → 22
    名前解決に失敗した場合は文字列 ID として返す。
    """
    raw = raw.strip()
    if raw.isdigit():
        return int(raw)
    from src.utils.dataset import resolve_badge
    resolved = resolve_badge(raw)
    if resolved != raw:  # DB の Num_Badge に一致 ("2B" → "2-alt")
        return resolved
    try:
        from src.pipeline.natural_parser import _build_name_lookup
        lookup = _build_name_lookup()
        if raw in lookup:
            num_str = lookup[raw]
            return int(num_str) if num_str.isdigit() else num_str
    except Exception:
        pass
    try:
        return int(raw)
    except ValueError:
        return raw


def _maybe_prompt_ambiguous_fields_interactively(
    char_params: list[dict], default_work_key: str, non_interactive: bool
) -> None:
    """実ターミナル (TTY) 上でのみ、RaceType 等の曖昧フィールドを対話確認する。

    char_params の各要素を必要に応じて in-place で更新する
    (scene 未指定なら確定させ、必要なら field_overrides を設定する)。
    非TTY (エージェント経由の Bash 実行・MCP の Cloud Run ジョブ) では即座に no-op で戻る。
    """
    if non_interactive or not sys.stdin.isatty():
        return

    from src.utils import find_character
    from src.utils.dataset import _AMBIGUOUS_FIELD_SPECS, describe_ambiguous_field_resolutions

    for cp in char_params:
        form = cp.get("form", "corefolder")
        applicable_specs = [s for s in _AMBIGUOUS_FIELD_SPECS if form in s.forms]
        if not applicable_specs:
            continue

        record = find_character(cp["num"], cp.get("work_key", default_work_key))
        if record is None:
            continue

        existing_overrides: dict[str, str] = dict(cp.get("field_overrides") or {})

        if not cp.get("scene"):
            cp["scene"] = generate_random_scene(record, form) or ""
            # ↑ ここで scene を確定させておくことで、後段の Stage1 が別のランダムシーンを
            #   再生成して自動判定と食い違う事態を防ぐ。

        resolutions = describe_ambiguous_field_resolutions(
            record, form, scene=cp["scene"], field_overrides=existing_overrides
        )
        for spec in applicable_specs:
            if spec.field_name in existing_overrides:
                continue  # 既に明示指定済み
            info = resolutions.get(spec.field_name)
            if not info or len(info.get("candidates") or []) < 2:
                continue  # 曖昧ではない

            candidates = info["candidates"]
            print(f"\n[確認] #{cp['num']} の「{spec.label_ja}」候補が複数あります:")
            for i, c in enumerate(candidates, start=1):
                marker = " <- 自動選択" if c.get("value") == info.get("value") else ""
                print(f"  {i}) {c.get('value')} — {c.get('about_JP', '')}{marker}")
            print(f"  自動判定理由: {info.get('reasoning') or '(なし)'}")

            try:
                choice = input("  Enter で確定 / 番号で上書き > ").strip()
            except (EOFError, KeyboardInterrupt):
                choice = ""
            if choice:
                try:
                    idx = int(choice) - 1
                except ValueError:
                    idx = -1
                if 0 <= idx < len(candidates):
                    existing_overrides[spec.field_name] = str(candidates[idx].get("value", ""))
                    print(f"  → 上書き: {existing_overrides[spec.field_name]}")
                else:
                    print("  無効な入力のため自動選択を使用します。")

        if existing_overrides:
            cp["field_overrides"] = existing_overrides


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "画像生成パイプライン (5 ステージ):\n"
            "  Stage1: コマンド解析 + OpenAI/Gemini でプロンプト生成\n"
            "  Stage2: キャラクター選定 + 創作 DB から原典画像・特徴を取得\n"
            "  Stage3: Adobe 非Firefly 構図ガイド + Gemini Imagen でラフ 5 案生成\n"
            "  Stage4: OpenAI Vision で違反分析 + Gemini i2i で修正\n"
            "  Stage5: Canva で作風調整・仕上げ → 完成画像 3 枚固定生成"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # キャラクター指定 (いずれか)
    char_group = parser.add_mutually_exclusive_group()
    char_group.add_argument(
        "--badge", "--num", dest="num", type=str,
        help="キャラクターのバッジ (DB の Num_Badge) / 番号 / 特殊ID / 名前 (例: 57 / '2B' / '2-alt' / 'バイナ')。シーン未指定時はランダム生成。",
    )
    char_group.add_argument(
        "--nums",
        help=(
            "複数キャラクター番号 カンマ区切り (例: 25,57)。"
            "2 件以上指定すると全員を 1 枚に合同生成する (マルチキャラクターシーン)。"
        ),
    )
    char_group.add_argument(
        "--natural",
        metavar="TEXT",
        help=(
            "自然文でリクエスト — LLM がキャラクター・シーン等を抽出する。\n"
            "例: 'コアフォルダ姿の25(フィズ)がチョコレートを咥えている絵'"
        ),
    )
    parser.add_argument(
        "--story",
        metavar="FILE",
        help="短編ストーリーファイル — --natural と同様に LLM がパースする。",
    )

    parser.add_argument(
        "--form", choices=["corefolder", "humanoid"], default="corefolder",
        help="生成する形態 (デフォルト: corefolder)",
    )
    parser.add_argument("--work", default="#Works_NumberTales", help="作品キー")
    parser.add_argument(
        "--out", default=None,
        help="出力ベースディレクトリ (省略時は OUTPUT_BASE_DIR / 'output')",
    )
    parser.add_argument(
        "--scene", default="",
        help="シーン・ポーズ説明。省略すると Stage 1 でキャラクターに合ったシーンを自動生成する。",
    )
    parser.add_argument("--style", default="", help="作風ヒント (例: 'watercolor')")
    parser.add_argument("--composition", default="", help="構図ヒント (例: 'bust shot')")
    parser.add_argument("--background", default="", help="背景ヒント")
    parser.add_argument(
        "--costume", default="",
        help=(
            "衣装の指定。DB にある衣装の名前 (例: miko) ならその衣装を、それ以外の文は衣装差分として描く。\n"
            "例: 'miko' / '黒いワンピース姿の差分' / 'summer school uniform variation'"
        ),
    )
    parser.add_argument(
        "--state", default="",
        help=(
            "状態の指定。DB にある状態の名前 (例: afterChanged, beasted) ならその状態を、\n"
            "それ以外の文は体型と着用物だけを変える指定として描く。"
        ),
    )
    parser.add_argument(
        "--states", default="",
        help="--nums の各キャラクターの状態 (--nums と同じ順に ; 区切り。空欄は既定)。",
    )
    parser.add_argument(
        "--field-override", action="append", default=None, dest="field_override",
        metavar="FIELD=VALUE",
        help=(
            "RaceType 等の曖昧フィールド（複数候補から1つ選ぶ必要があるもの）を明示指定する。\n"
            "繰り返し指定可能。未指定フィールドはシーン文脈から LLM が自動判定する。\n"
            "例: --field-override RaceType=最終的な設計目標 --field-override Height_cm=190"
        ),
    )
    parser.add_argument(
        "--skip-canva", action="store_true",
        help="Stage 5 の Canva フィニッシングをスキップ (CANVA_ACCESS_TOKEN 不要)",
    )
    parser.add_argument(
        "--correction-mode", choices=["t2i", "stage3"], default="t2i",
        dest="correction_mode",
        help=(
            "Stage 4 での重度違反時の対処モード (デフォルト: t2i)\n"
            "  t2i:    Stage 4 内で T2I フル再生成\n"
            "  stage3: Stage 3 に差し戻してラフを再生成"
        ),
    )
    parser.add_argument(
        "--iterate-from", default=None, dest="iterate_from",
        metavar="PATH",
        help=(
            "前回生成画像 (ファイルパスまたは run-dir) を起点に i2i モードで Stage 3 を実行する。\n"
            "Stage 4 (違反修正) / Stage 5 (Canva) は通常通り走る。\n"
            "例: output/20260616/.../num057_corefolder_01.jpg"
        ),
    )
    parser.add_argument(
        "--revisions", default=None,
        metavar="TEXT",
        help=(
            "修正指示。';' または改行で複数項目に分割される。--iterate-from と組み合わせて使用。\n"
            "例: '尻尾は元のまま; 表情だけ笑顔にして'"
        ),
    )
    parser.add_argument(
        "--images", default=None, metavar="JSON|FILE",
        help=(
            "依頼者が渡す入力画像。JSON の配列か、それを書いた .json ファイル。\n"
            "  [{\"role\": \"base|markup|composition|reference\", \"path\": \"output/… か references/…\",\n"
            "    \"provenance\": \"own_generated|own_work|own_photo\", \"note\": \"reference の用途\"}]\n"
            "役割ごとの枚数と渡すステージは docs/usage-iterate.md の「入力画像」を参照。"
        ),
    )
    parser.add_argument(
        "--quick", action="store_true",
        help=(
            "軽い加筆。起点 (--iterate-from か、役割 base の画像) の絵を 1 回だけ編集し、完成画像 1 枚を保存する。\n"
            "Stage 1 の LLM 加工・Stage 2 の観察・Stage 4 の検査・Canva を省く。単体 (--badge) だけ。"
        ),
    )
    parser.add_argument(
        "--dry-run", action="store_true", dest="dry_run",
        help="生成せず、プロンプトの土台・選べる状態と衣装・役割の付いた画像の一覧を表示する (課金なし)",
    )
    parser.add_argument(
        "--rough-provider", default="gemini", dest="rough_provider",
        choices=["gemini", "sdxl-guide", "sdxl", "both"],
        help=(
            "Stage 3 のラフ生成プロバイダ (既定: gemini)。\n"
            "  sdxl-guide: SDXL でコアフォルダのアタリ(構図/作風の下敷き)を生成し、\n"
            "              Gemini ラフの追加参照に渡す (個体正確性は Gemini+DB が担う・GCE VM 課金注意)\n"
            "  sdxl / both: 旧・併走ピアモード (非推奨)。警告のうえ sdxl-guide に読み替える。\n"
            "単体キャラ実行のみ対応。合同 (--nums) では gemini 固定。"
        ),
    )
    parser.add_argument(
        "--prefer-gemini-parse", action="store_true",
        help="--natural / --story のパース時に Gemini を OpenAI より優先する",
    )
    parser.add_argument(
        "--non-interactive", action="store_true", dest="non_interactive",
        help=(
            "実ターミナル (TTY) 実行時でも、曖昧フィールドの対話確認プロンプトを出さない。\n"
            "CI・スクリプト等、TTY はあるが対話させたくない場合に指定する。"
        ),
    )
    args = parser.parse_args()

    # 旧・併走ピアモード (sdxl/both) は廃止。sdxl-guide (アタリ→Gemini参照) に読み替える。
    if args.rough_provider in ("sdxl", "both"):
        print(
            f"[WARN] --rough-provider {args.rough_provider} は廃止されました。"
            "sdxl-guide (SDXL アタリを Gemini の構図参照に使う) に読み替えます。"
        )
        args.rough_provider = "sdxl-guide"

    field_override: dict[str, str] = {}
    for kv in (args.field_override or []):
        if "=" not in kv:
            sys.exit(f"[ERROR] --field-override は FIELD=VALUE 形式で指定してください: {kv!r}")
        k, v = kv.split("=", 1)
        k = k.strip()
        if not k:
            sys.exit(f"[ERROR] --field-override のフィールド名が空です: {kv!r}")
        field_override[k] = v.strip()

    # ──── 入力モード別キャラクターパラメータの収集 ────

    char_params: list[dict] = []

    if args.natural or args.story:
        if args.dry_run or args.images:
            sys.exit("[ERROR] --dry-run と --images は --badge / --nums と一緒に使ってください"
                     "（--natural / --story は対象外です）。")
        from src.pipeline.natural_parser import parse_generation_request

        if args.story:
            story_path = Path(args.story)
            if not story_path.exists():
                sys.exit(f"[ERROR] --story ファイルが見つかりません: {args.story}")
            text = story_path.read_text(encoding="utf-8").strip()
            print(f"[INFO] ストーリーファイル読み込み: {args.story} ({len(text)} 文字)")
        else:
            text = args.natural

        char_params = parse_generation_request(
            text, prefer_gemini=args.prefer_gemini_parse
        )
        if not char_params:
            sys.exit("[ERROR] --natural / --story からキャラクターパラメータを抽出できませんでした。")

        # CLI 追加指定をマージ (CLI 指定が優先)
        for cp in char_params:
            if args.scene and not cp.get("scene"):
                cp["scene"] = args.scene
            if args.style and not cp.get("style"):
                cp["style"] = args.style
            if args.composition and not cp.get("composition"):
                cp["composition"] = args.composition
            if args.background and not cp.get("background"):
                cp["background"] = args.background
            if args.costume and not cp.get("costume"):
                cp["costume"] = args.costume
            if args.state and not cp.get("state"):
                cp["state"] = args.state
            if field_override and not cp.get("field_overrides"):
                cp["field_overrides"] = dict(field_override)
            if args.form != "corefolder":
                cp["form"] = args.form

    elif args.nums:
        raw_nums = [s.strip() for s in args.nums.split(",") if s.strip()]
        nums: list[int | str] = [_resolve_num_arg(s) for s in raw_nums]
        if not nums:
            sys.exit("[ERROR] --nums に有効な番号がありません。")
        nums_states = [s.strip() for s in args.states.split(";")] if args.states else []
        if len(nums_states) > len(nums):
            sys.exit("[ERROR] --states の件数が --nums のキャラクター数より多くなっています。")
        for index, n in enumerate(nums):
            char_params.append({
                "state": nums_states[index] if index < len(nums_states) else args.state,
                "num": n,
                "form": args.form,
                "scene": args.scene,
                "style": args.style,
                "composition": args.composition,
                "background": args.background,
                "costume": args.costume,
                "field_overrides": dict(field_override),
                "work_key": args.work,
            })

    elif args.num:
        char_params.append({
            "state": args.state,
            "num": _resolve_num_arg(args.num),
            "form": args.form,
            "scene": args.scene,
            "style": args.style,
            "composition": args.composition,
            "background": args.background,
            "costume": args.costume,
            "field_overrides": dict(field_override),
            "work_key": args.work,
        })

    else:
        parser.error("--num / --nums / --natural / --story のいずれかを指定してください。")

    if not args.dry_run:
        _maybe_prompt_ambiguous_fields_interactively(
            char_params, default_work_key=args.work, non_interactive=args.non_interactive
        )

    if args.dry_run:
        first = char_params[0]
        try:
            plan = plan_pipeline(
                [cp["num"] for cp in char_params], [cp.get("form", args.form) for cp in char_params],
                first.get("work_key", args.work),
                scene=first.get("scene", "") or args.scene, style=first.get("style", args.style),
                composition=first.get("composition", args.composition),
                background=first.get("background", args.background), costume=first.get("costume", args.costume),
                states=[cp.get("state", args.state) for cp in char_params],
                iterate_from=args.iterate_from, revisions=args.revisions, images=args.images, out_dir=args.out,
                quick=args.quick, field_overrides=first.get("field_overrides") or field_override,
            )
        except ValueError as err:
            print(f"[ERROR] {err}")
            sys.exit(1)
        print("[INFO] --dry-run のため生成しません。")
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return

    # ──── パイプライン実行 ────

    if args.quick:
        if len(char_params) != 1:
            sys.exit("[ERROR] --quick は単体 (--badge) だけで使えます。")
        cp = char_params[0]
        result = run_quick_edit(
            num=cp["num"], form=cp.get("form", "corefolder"), work_key=cp.get("work_key", args.work),
            out_dir=args.out, iterate_from=args.iterate_from, revisions=args.revisions, images=args.images,
            costume=cp.get("costume", args.costume), state=cp.get("state", args.state),
            field_overrides=cp.get("field_overrides") or field_override,
        )
        print(f"\n[完了] ステータス: {result.status}")
        for err in result.errors:
            print(f"  [ERROR] {err}")
        for path in result.stage5_paths.get("all") or []:
            print(f"  完成画像 (quick): {path}")
        return

    if len(char_params) == 1:
        cp = char_params[0]
        result = run_image_pipeline(
            num=cp["num"],
            form=cp.get("form", "corefolder"),
            work_key=cp.get("work_key", args.work),
            out_dir=args.out,
            scene=cp.get("scene", ""),
            style=cp.get("style", ""),
            composition=cp.get("composition", ""),
            background=cp.get("background", ""),
            costume=cp.get("costume", args.costume),
            state=cp.get("state", args.state),
            field_overrides=cp.get("field_overrides") or field_override,
            skip_canva=args.skip_canva,
            correction_mode=args.correction_mode,
            iterate_from=args.iterate_from,
            revisions=args.revisions,
            rough_provider=args.rough_provider,
            images=args.images,
        )
        print(f"\n[完了] ステータス: {result.status}")
        if result.scene_used:
            print(f"  シーン: {result.scene_used}")
        if result.errors:
            for err in result.errors:
                print(f"  [ERROR] {err}")
        s5 = result.stage5_paths.get("all") or []
        s4_all = result.stage4_paths.get("all") or []
        s3_gemini = result.stage3_paths.get("gemini") or []
        if s5:
            print(f"  完成画像 (Stage5): {len(s5)} 枚")
        if s4_all:
            print(f"  修正済みラフ (Stage4): {len(s4_all)} 枚")
        if s3_gemini:
            print(f"  ラフ (Stage3): Gemini {len(s3_gemini)} 枚")
        s3_sdxl_guide = result.stage3_paths.get("sdxl_guide") or []
        if s3_sdxl_guide:
            print(f"  アタリ (Stage3): SDXL {len(s3_sdxl_guide)} 枚 (Gemini 参照用)")

    else:
        # 2 件以上の --nums → 全員を 1 枚に合同生成
        if args.rough_provider != "gemini":
            print("[WARN] --rough-provider (sdxl-guide) は合同生成 (--nums) では未対応です。gemini で続行します。")
        combined_nums = [cp["num"] for cp in char_params]
        combined_scene = char_params[0].get("scene", "") or args.scene
        combined_forms = [cp.get("form", args.form) for cp in char_params]
        res = run_combined_pipeline(
            nums=combined_nums,
            forms=combined_forms,
            form=combined_forms[0],
            work_key=char_params[0].get("work_key", args.work),
            out_dir=args.out,
            scene=combined_scene,
            style=char_params[0].get("style", args.style),
            composition=char_params[0].get("composition", args.composition),
            background=char_params[0].get("background", args.background),
            costume=char_params[0].get("costume", args.costume),
            states=[cp.get("state", "") for cp in char_params],
            field_overrides=char_params[0].get("field_overrides") or field_override,
            skip_canva=args.skip_canva,
            correction_mode=args.correction_mode,
            iterate_from=args.iterate_from,
            revisions=args.revisions,
            images=args.images,
        )
        nums_label = "+".join(f"#{_fmt_num(n)}" for n in res.nums)
        scene_preview = (res.scene_used[:24] + "...") if len(res.scene_used) > 24 else res.scene_used
        print(f"\n[完了] {nums_label} / ステータス: {res.status} / シーン: {scene_preview}")
        if res.errors:
            for err in res.errors:
                print(f"  [ERROR] {err}")
        s5 = res.stage5_paths.get("all") or []
        s3 = res.stage3_paths.get("gemini") or []
        if s5:
            print(f"  完成画像 (Stage5): {len(s5)} 枚")
        if s3:
            print(f"  Gemini ラフ (Stage3): {len(s3)} 枚")


if __name__ == "__main__":
    from src.pipeline.design_reference import ReferenceConfirmationRequired, ReferenceCancelled
    try:
        main()
    except (ReferenceConfirmationRequired, ReferenceCancelled) as exc:
        print(f"[確認待ち/中止] {exc}")
        sys.exit(2)
