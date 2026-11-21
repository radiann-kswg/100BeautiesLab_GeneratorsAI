"""
pipeline/correction_generator.py — Stage 4: 違反特徴の除去 + 構図修正
Copyright © RadianN_kswg — CC BY-NC 4.0

Stage 3 のラフ5案を入力に、以下の2ステップで修正を行う:

  1. 分析 (OpenAI Vision / GPT-4o):
     各ラフ画像をキャラクタースペックと照合し、
     「形態として存在しない特徴」「構図の破綻」を列挙する。
     (OPENAI_API_KEY 未設定の場合はスキップし Gemini のみで修正)

  2. 修正:
     - 軽度違反 (< _SEVERE_VIOLATION_THRESHOLD): gpt-image-1 images.edit で外科的 i2i 修正。
       OPENAI_CORRECTION_MODEL 未設定または失敗時は Gemini i2i にフォールバック。
     - 重度違反 (≥ _SEVERE_VIOLATION_THRESHOLD): Gemini T2I でフル再生成 (形態リセット)。
     - 違反なし・分析スキップ: pass-through。

出力: stage4_correct/ に修正済み画像を保存。
Stage 5 はここで生成された画像 (最大 5 枚) を受け取り、3 枚を仕上げる。
"""

from __future__ import annotations

import base64
import json
import os
import re
import sys
import time
from pathlib import Path

# 違反件数がこの値以上なら i2i ではなく T2I（フル再生成）に切り替える。
# i2i は元画像の構造を維持するため、全身humanoidのような根本的な形態誤りを
# 1回では修正しきれない。T2I にすることで形態をリセットする。
_SEVERE_VIOLATION_THRESHOLD = 3

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.utils.dataset import (  # noqa: E402
    extract_color_palette,
    generation_ai_hints,
    IMAGE_TEXT_POLICY,
    _build_number_print_block,
    _format_color_palette_lines,
    record_num,
)

_NUMBER_FIX_RE = re.compile(r"番号|数字|字形|number|digit|glyph|font", re.IGNORECASE)


def _number_block_if_targeted(record: dict, form: str, fixes: str) -> str:
    """i2i 最小修正は「それ以外は起点画像に忠実」が主眼。番号が修正対象のときだけ
    字形ブロックを足し、無関係な修正で番号を描き直させない。"""
    return _build_number_print_block(record, form) if _NUMBER_FIX_RE.search(fixes or "") else ""


def _identity_tags(record: dict, form: str, limit: int = 8) -> str:
    """維持させる識別要素の一覧。common だけでは種族の 1 語しか無いレコードがあるので
    (髪・瞳が形態別にだけ書かれている。CreationsDB #67)、その形態の体の特徴と付属物も足す。"""
    hints = generation_ai_hints(record)
    common = hints.get("common") or {}
    form_hints = (hints.get("forms") or {}).get(form) or {}
    if form_hints.get("ai_tags"):
        tags = [*(common.get("identity_tags") or []), *(common.get("immutable_traits") or []),
                *(form_hints.get("ai_tags") or [])]
    else:
        # ai_tags が未収録の旧レコードだけ、旧 silhouette_notes をフォールバックに使う。
        notes = form_hints.get("silhouette_notes") or {}
        tags = [*(common.get("identity_tags") or []), *(common.get("immutable_traits") or []),
                *(notes.get("body_description") or []), *(notes.get("attached_items") or [])]
    return ", ".join(list(dict.fromkeys(tag for tag in tags if isinstance(tag, str) and tag.strip()))[:limit])


def _ask_openai_json(system: str, content: list[dict]) -> dict:
    from openai import OpenAI

    response = OpenAI(api_key=os.environ["OPENAI_API_KEY"]).chat.completions.create(
        model=os.environ.get("GPT_MODEL", "gpt-4o"),
        messages=[{"role": "system", "content": system}, {"role": "user", "content": content}],
        max_tokens=400,
        response_format={"type": "json_object"},
    )
    return json.loads((response.choices[0].message.content or "{}").strip())


def check_joint_identity_mixing(image_path: "Path | str", characters: "list[tuple[dict, str]]", ask=None,
                                renders: "list[Path | str] | None" = None) -> dict:
    """合同の絵 (構図ラフ・完成画像) で、体数が合っているか、識別要素が持ち主以外のキャラクターに
    描かれていないかを OpenAI Vision で見る。

    characters は (レコード, 形態) の並び。``{"mixed": [指摘...], "skipped": bool}`` を返す。直しはしない。
    ``renders`` は characters と同じ順の、検査を通った単体レンダー。渡すと配色の基準として添付し、
    髪・尾・首輪などの色相が明らかに違う部位も指摘させる (合成で尾や首輪の色が変わることがある)。
    ``ask`` はテスト用の差し替え口 (system と content を受け、JSON の dict を返す)。
    """
    from src.utils.dataset import extract_char_name
    from src.utils.image_io import load_reference_bytes

    loaded = load_reference_bytes(Path(image_path)) if Path(image_path).is_file() else None
    if loaded is None or (ask is None and not os.environ.get("OPENAI_API_KEY")):
        return {"mixed": [], "skipped": True}
    raw, mime = loaded
    listed = "\n".join(     # 番号を添えるのは数字だけのとき。"2-alt" や "2B" は識別子で、絵に描く表記ではない
        f"- {extract_char_name(record)} ({form}): "
        + (f"番号 {record_num(record)}; " if str(record_num(record)).isdigit() else "")
        + _identity_tags(record, form)
        for record, form in characters
    )
    basis = [(extract_char_name(record), loaded_render)
             for (record, _), path in zip(characters, renders or [])
             if path is not None
             and Path(path).is_file()
             and (loaded_render := load_reference_bytes(Path(path)))]
    system = (
        "あなたは複数のキャラクターが描かれたイラストの検査AIです。**JSONのみ**を返してください: "
        '{"mixed": ["指摘1", ...]}'
    )
    user = (
        f"この画像には、次の {len(characters)} 体のキャラクターが 1 体ずつ描かれているはずです。\n"
        f"[キャラクターと識別要素]\n{listed}\n\n"
        "[検査のしかた]\n"
        "- あるキャラクターの番号・名前の表記・ラベル・タグ・首輪・紋章・髪飾りが、別のキャラクターにも描かれていれば、"
        "mixed に「<描かれている側の名前> に <持ち主の名前> の <要素>」の形で入れる。\n"
        f"- 描かれているキャラクターが {len(characters)} 体でなければ、mixed に「体数: <何体いるか>。{len(characters)} 体を描く」と入れる。\n"
        "- 設定のうえで両方が持つ特徴 (同じ種族の耳、同じ色の髪など) は入れない。\n"
        + ("- 2 枚目以降は、各キャラクターの単体レンダー (配色の基準)。1 枚目の検査対象で、髪・尾・耳・瞳・首輪・番号の"
           "色相が単体レンダーと明らかに違う部位があれば、mixed に「配色: <名前> の <部位> が <検査対象での色> "
           "(基準は <色>)」と入れる。陰影・照明による濃淡の差、ポーズや構図の違いは入れない。\n" if basis else "")
        + "- 問題が無ければ空配列を返す。"
    )
    content = [{"type": "text", "text": user}, {"type": "image_url", "image_url": {
        "url": f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"}}]
    for name, (render_raw, render_mime) in basis:
        content.append({"type": "text", "text": f"{name} の単体レンダー (配色の基準。検査対象ではない):"})
        content.append({"type": "image_url", "image_url": {
            "url": f"data:{render_mime};base64,{base64.b64encode(render_raw).decode('ascii')}"}})
    try:
        answer = (ask or _ask_openai_json)(system, content)
        if not isinstance(answer, dict):
            return {"mixed": [], "skipped": True}
        found = answer.get("mixed")
    except Exception as err:
        print(f"[WARN] Stage5 識別要素の取り違えの検査に失敗: {err}")
        return {"mixed": [], "skipped": True}
    if not isinstance(found, list) or not all(isinstance(item, str) for item in found):
        return {"mixed": [], "skipped": True}
    return {"mixed": [item for item in found if item], "skipped": False}


def _palette_lines(spec: dict, limit: int = 6) -> str:
    """spec の `color_palette` (Stage 2 で DB から収集) をプロンプト用の行へ整形。"""
    entries = spec.get("color_palette") or []
    if not entries:
        return ""
    return "\n".join(_format_color_palette_lines(entries[:limit]))


def _record_palette_summary(record: dict, form: str, limit: int = 4) -> str:
    """i2i 修正プロンプト用に配色を 1 行へ圧縮する (例: `主色 #FF8682 (chest, hair)`)。"""
    entries = extract_color_palette(record, form)[:limit]
    if not entries:
        return ""
    parts: list[str] = []
    for entry in entries:
        text = f"{entry['role_ja']} {entry['hex']}"
        if entry["applies_to"]:
            text += f" ({', '.join(entry['applies_to'])})"
        parts.append(text)
    return " / ".join(parts)


# ──────────────────────────────────────────
# OpenAI Vision による違反分析
# ──────────────────────────────────────────

def _analyze_rough_with_openai(
    image_path: Path, spec: dict, ref_image_path: Path | None = None,
    markup_path: Path | None = None,
) -> dict:
    """OpenAI Vision でラフ画像の違反特徴・構図問題を分析する。

    ref_image_path が指定されている場合は公式 DB 参照画像を 2 枚目として添付し、
    左右の向き・非対称要素の配置が原典と反転していないかも検査する
    （i2i 起点画像由来の左右反転を Stage 4 で検出・修正するため）。

    markup_path が指定されている場合は、依頼者の赤入れ画像を添付し、指示した場所が直っているか、
    赤い印や指示の文字が絵に残っていないかを composition_issues に数える。

    Returns
    -------
    {
        "violations": list[str],         — 存在すべきでない特徴
        "composition_issues": list[str], — 構図の破綻
        "overall_ok": bool,
        "skipped": bool,
    }
    """
    try:
        from openai import OpenAI
    except ImportError:
        return {"violations": [], "composition_issues": [], "overall_ok": True, "skipped": True}

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return {"violations": [], "composition_issues": [], "overall_ok": True, "skipped": True}

    if not image_path.exists():
        return {"violations": [], "composition_issues": [], "overall_ok": True, "skipped": True}

    gpt_model = os.environ.get("GPT_MODEL", "gpt-4o")
    form = spec.get("form", "corefolder")
    violation_list = "\n".join(f"- {v}" for v in spec.get("violation_features", []))
    immutable = ", ".join(spec.get("immutable_traits") or [])
    char_name = spec.get("char_name", "Unknown")
    palette_lines = _palette_lines(spec)

    # 配色は DB の実測値 (設定画のカラーチップ由来)。明らかな色相ズレのみ違反として拾わせる。
    # 陰影・ハイライト・照明差による濃淡は許容しないと、正常な絵まで違反判定されてしまう。
    palette_section = (
        "\n[配色仕様 (DB実測値)]\n"
        f"{palette_lines}\n"
        "指定部位の色相が明らかに異なる場合のみ violations に追加してください"
        "（陰影・ハイライト・照明による濃淡差は違反ではありません）。\n"
        if palette_lines
        else ""
    )

    # ── 原典照合 (公式 DB 参照画像がある場合のみ): 左右整合 + 欠落/蛇足 ──
    has_ref = bool(ref_image_path and ref_image_path.exists())
    chirality_section = (
        "\n[原典照合]\n"
        "2枚目の画像は公式 DB 参照 (原典) です。1枚目 (検査対象) と比較してください。\n"
        "- 左右の向き・非対称要素の配置 (尻尾の束構成・マーキング位置・髪の分け目など) が"
        "原典と左右反転している場合は、violations に「左右反転: <要素>」の形式で追加。\n"
        "- 原典に無い装飾・模様・アクセサリ・付属物が描き足されている場合は、"
        "violations に「蛇足: <要素>」の形式で追加。\n"
        "- 原典にある識別要素 (耳・尻尾の本数/形・髪型・アクセサリ・番号バッジ・模様) が"
        "欠けている/形が違う/数が違う場合は、missing に「<要素>: <原典ではどうか>」の形式で追加。\n"
        "追加の公式部位図と番号の字形・線幅・間隔・切れ目・装飾を比較し、汎用フォントへの置換も missing に追加。\n"
        "部位図を全身と比較しないこと。指定位置は全体図とDB部位別仕様で確認。\n"
        "ポーズや構図の違いによる自然な差・左右対称な要素は違反ではありません。\n"
        if has_ref
        else ""
    )

    system = (
        f"あなたは{spec.get('work_title', 'ナンバーテールズ')}キャラクター「{char_name}」の{form}形態イラストの品質検査AIです。\n"
        "画像に対して以下を確認し、**JSONのみ**を返してください（説明文・マークダウン不要）:\n"
        '{"violations": ["違反内容1", ...], "missing": ["欠落要素1", ...], '
        '"composition_issues": ["構図問題1", ...], "overall_ok": true}'
    )
    user = (
        f"このイラストを検査してください。\n"
        f"形態: {form}\n"
        f"不変特徴 (必ず存在するべき・違反扱い禁止): {immutable}\n"
        f"対象形態の特徴 (AIHints ai_tags): {', '.join(spec.get('ai_tags') or [])}\n"
        "上記の不変特徴が画像に無い・数や形が違う場合は missing に追加してください。\n"
        f"以下の要素が存在する場合は violations に追加してください"
        f"（ただし上記の不変特徴として期待されるものは violations に含めないこと）:\n{violation_list}\n"
        f"{palette_section}"
        f"{spec.get('number_print_spec', '')}\n"
        f"{spec.get('appearance_detail_spec', '')}\n"
        f"{chirality_section}\n"
        "構図として明らかに破綻している点があれば composition_issues に追加してください。\n"
        "この絵は対象のキャラクター 1 体だけを描くものです。同じキャラクターが 2 体以上いる、または別のキャラクターが"
        "一緒に描かれている場合は、composition_issues に「体数: <何体いるか>。1 体だけを描く」と追加してください"
        "（鏡や水面への映り込みは数えません）。\n"
        "同じ番号・ラベル・タグが 2 か所以上に描かれている場合は、violations に「重複: <要素> が <何か所>」と追加してください"
        "（設定で複数あるものは除きます）。\n"
        "問題がなければ overall_ok: true として violations / missing / composition_issues は空リストにしてください。"
    )

    has_markup = bool(markup_path and Path(markup_path).is_file())
    if has_markup:
        user += (
            "\n\n[赤入れの確認]\n"
            "最後に添付した「赤入れ画像」は、描き直す前の絵に依頼者が赤で指示を描き込んだものです"
            "（検査対象の絵ではありません）。\n"
            "- 赤い線・丸・矢印・短い書き込みが指す場所が、検査対象の絵で指示のとおりに直っていなければ、"
            "composition_issues に「赤入れ未反映: <場所と内容>」の形式で追加。\n"
            "- 赤い印や指示の文字そのものが検査対象の絵に残っていれば、"
            "composition_issues に「赤入れの印が残っている: <場所>」の形式で追加。\n"
            "- 赤入れ画像の中のキャラクターの外見は、違反・欠落の判定に使わないこと。"
        )

    if spec.get("design_reference"):
        from src.pipeline.design_reference import design_reference_block
        user = design_reference_block(spec["design_reference"]) + user

    def _encode_image(path: Path) -> tuple[str, str]:
        ext = path.suffix.lstrip(".").lower()
        mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}.get(ext, "image/png")
        return mime, base64.b64encode(path.read_bytes()).decode("utf-8")

    mime, img_b64 = _encode_image(image_path)
    content: list[dict] = [
        {"type": "text", "text": user},
        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{img_b64}"}},
    ]
    if has_ref:
        ref_mime, ref_b64 = _encode_image(ref_image_path)  # type: ignore[arg-type]
        content.append(
            {"type": "image_url", "image_url": {"url": f"data:{ref_mime};base64,{ref_b64}"}}
        )

    for detail_path in spec.get("detail_reference_paths") or []:
        path = Path(detail_path)
        if not path.is_file() or path == ref_image_path:
            continue
        from src.utils.image_io import load_reference_bytes
        loaded = load_reference_bytes(path)
        if loaded is None:
            continue
        raw, detail_mime = loaded
        content.append({"type": "text", "text": "公式部位図 (この部位の形・字形のみ照合): " + path.name})
        content.append({"type": "image_url", "image_url": {
            "url": f"data:{detail_mime};base64,{base64.b64encode(raw).decode('ascii')}"}})

    if has_markup:
        from src.utils.image_io import load_reference_bytes
        loaded = load_reference_bytes(Path(markup_path))  # type: ignore[arg-type]
        if loaded is not None:
            raw, markup_mime = loaded
            content.append({"type": "text", "text": "赤入れ画像 (描き直す前の絵への指示書き。検査対象ではない):"})
            content.append({"type": "image_url", "image_url": {
                "url": f"data:{markup_mime};base64,{base64.b64encode(raw).decode('ascii')}"}})

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=gpt_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": content},
            ],
            max_tokens=500,
            response_format={"type": "json_object"},
        )
        raw = (response.choices[0].message.content or "{}").strip()
        result = json.loads(raw)
        result.setdefault("violations", [])
        result.setdefault("missing", [])
        result.setdefault("composition_issues", [])
        result.setdefault("overall_ok", True)
        result["skipped"] = False
        return result
    except Exception as err:
        print(f"[WARN] Stage4 OpenAI Vision 分析失敗: {err}")
        return {"violations": [], "composition_issues": [], "overall_ok": True, "skipped": True}


# ──────────────────────────────────────────
# Gemini i2i による修正適用
# ──────────────────────────────────────────

def _apply_correction_gemini(
    record: dict,
    form: str,
    rough_path: Path,
    analysis: dict,
    prompts: dict,
    stage_dir: Path,
    work_key: str,
    index: int,
    use_t2i: bool = False,
) -> list[Path]:
    """違反分析結果を基に Gemini で修正を適用する。

    use_t2i=True の場合は i2i をスキップして T2I（フル再生成）を行う。
    違反が重篤（_SEVERE_VIOLATION_THRESHOLD 以上）な場合に使用する。
    """
    from src.gemini.generate import generate_image

    violations = analysis.get("violations") or []
    missing = analysis.get("missing") or []
    comp_issues = analysis.get("composition_issues") or []
    # T2I はフル再生成なので全仕様を含む base_gemini を使う。
    # i2i はソース画像がスタイルアンカーになるため、修正ターゲットのみに絞った短いプロンプトを使う。
    # base_gemini を i2i に使うと「別のポーズで描いてください」という再生成指示が競合し作風が崩れる。
    base_prompt = prompts.get("base_gemini", "") or prompts.get("gemini", "")

    if use_t2i:
        avoid_note = ""
        if violations:
            avoid_items = "; ".join(violations[:4])
            avoid_note = f"\n\n[特に避けること (前回生成で検出された違反)]\n- {avoid_items}"
        if missing:
            avoid_note += "\n\n[必ず描くこと (前回生成で欠落)]\n- " + "; ".join(missing[:4])
        correction_prompt = base_prompt + avoid_note
        iterate_path = None
        print(f"[Stage4] rough_{index:02d}: 違反 {len(violations)} 件 → T2I (フル再生成)")
    else:
        # i2i 専用: 最小限の修正指示のみ。ソース画像の作風・構図を最大限維持させる。
        identity_tags = _identity_tags(record, form)
        num_val = record_num(record)
        palette_summary = _record_palette_summary(record, form)
        palette_line = f"- 配色 (DB実測値): {palette_summary}\n" if palette_summary else ""

        fix_lines = "\n".join(f"- {v} を除去または修正" for v in violations)
        fix_lines += "".join(f"\n- {m} — 公式原典どおりに描き足す/直す" for m in missing)
        comp_lines = (
            "\n[構図修正]\n" + "\n".join(f"- {c}" for c in comp_issues) if comp_issues else ""
        )
        correction_prompt = (
            "[i2i 最小修正 — 起点画像の作風・構図・フォルムを最大限維持すること]\n"
            "以下の項目のみを修正し、それ以外は起点画像に忠実に保つこと。"
            "識別要素の形・数・色は添付の公式原典を正とし、原典に無い要素は足さないこと。\n\n"
            f"[修正対象]\n{fix_lines}{comp_lines}\n\n"
            "[維持すること]\n"
            f"- 形態: {form}\n"
            f"- 識別要素: {identity_tags}\n"
            f"{palette_line}"
            + (f"- キャラクター番号: #{num_val}\n" if str(num_val).isdigit() else "") +
            "- 作風（線の太さ・塗りスタイル）は入力画像に合わせること\n"
            f"{IMAGE_TEXT_POLICY}"
            f"{_number_block_if_targeted(record, form, fix_lines)}"
        )
        iterate_path = str(rough_path)

    correct_subdir = stage_dir / f"rough_{index:02d}_corrected"
    correct_subdir.mkdir(parents=True, exist_ok=True)

    try:
        return generate_image(
            num=record_num(record),
            form=form,
            work_key=work_key,
            out_dir=str(correct_subdir),
            count=1,
            iterate_from=iterate_path,
            prompt_override=correction_prompt,
            # i2i 修正でも DB 原典を添付する。以前は「原典に引っ張られて要素を足す」ため外して
            # いたが、原因は参照画像が無名で役割不明だったこと。generate_image が起点画像/原典の
            # 役割ラベルを各画像に付けるようになったので、原典なしで欠落特徴を直す方が害が大きい。
        )
    except SystemExit as err:
        print(f"[WARN] Stage4 Gemini 修正 (rough_{index:02d}): {err}")
        return []
    except Exception as err:
        print(f"[WARN] Stage4 Gemini 修正に失敗 (rough_{index:02d}): {type(err).__name__}: {err}")
        return []


# ──────────────────────────────────────────
# gpt-image-1 images.edit による外科的修正
# ──────────────────────────────────────────

def _apply_correction_openai(
    record: dict,
    form: str,
    rough_path: Path,
    analysis: dict,
    stage_dir: Path,
    work_key: str,
    index: int,
) -> list[Path]:
    """gpt-image-1 images.edit で軽度違反を外科的修正する。

    OPENAI_CORRECTION_MODEL が gpt-image-* 系、かつ OPENAI_API_KEY が設定されている
    場合のみ動作する。修正は英語の最小化プロンプトで行い、元画像の作風・構図を最大限維持する。
    失敗時は空リストを返し、呼び出し元が Gemini i2i にフォールバックする。
    """
    model = os.environ.get("OPENAI_CORRECTION_MODEL", "")
    if not model.startswith("gpt-image"):
        return []
    if not os.environ.get("OPENAI_API_KEY"):
        return []

    from src.openai.generate import generate_image_dalle

    violations = analysis.get("violations") or []
    comp_issues = analysis.get("composition_issues") or []
    identity_tags = _identity_tags(record, form)
    num_val = record_num(record)
    palette_summary = _record_palette_summary(record, form)
    palette_line = f"Color palette (from DB, keep): {palette_summary}\n" if palette_summary else ""

    fix_parts = ["; ".join(violations)] if violations else []
    missing = analysis.get("missing") or []
    if missing:
        fix_parts.append("restore/add as in the official design: " + "; ".join(missing))
    if comp_issues:
        fix_parts.append("; ".join(comp_issues) + " (composition fix)")
    all_fixes = "; ".join(fix_parts)

    correction_prompt = (
        "[Surgical i2i correction — preserve all visual style, form, and composition from input image]\n"
        f"Form: {form}, Character #{num_val}, Identity: {identity_tags}\n"
        f"{palette_line}"
        f"ONLY correct: {all_fixes}\n"
        "Keep EVERYTHING else identical to the input image.\n"
        f"{IMAGE_TEXT_POLICY}"
        f"{_number_block_if_targeted(record, form, all_fixes)}"
    )

    correct_subdir = stage_dir / f"rough_{index:02d}_corrected"
    correct_subdir.mkdir(parents=True, exist_ok=True)

    inter_sleep = float(os.environ.get("OPENAI_IMAGE_SLEEP", "6"))
    try:
        print(f"[Stage4-OpenAI] rough_{index:02d}: {model} images.edit で修正中 ({inter_sleep:.0f}秒待機後)...")
        time.sleep(inter_sleep)
        path = generate_image_dalle(
            num=num_val,
            form=form,
            work_key=work_key,
            out_dir=str(correct_subdir),
            prompt_override=correction_prompt,
            iterate_from=str(rough_path),
            model=model,
        )
        return [path] if path else []
    except SystemExit as err:
        print(f"[WARN] Stage4 OpenAI 修正 (rough_{index:02d}): {err}")
        return []
    except Exception as err:
        print(f"[WARN] Stage4 OpenAI 修正に失敗 (rough_{index:02d}): {type(err).__name__}: {err}")
        return []


# ──────────────────────────────────────────
# メイン関数
# ──────────────────────────────────────────

def correct_rough_images(
    record: dict,
    form: str,
    rough_results: dict[str, list[Path]],
    char_spec: dict,
    prompts: dict,
    pipeline_dir: Path,
    work_key: str = "#Works_NumberTales",
    correction_mode: str = "t2i",
    inputs: list[dict] | None = None,
) -> dict[str, list[Path]]:
    """Stage 4: ラフ画像の違反特徴を修正し、形態として違和感のない状態にする。

    Parameters
    ----------
    record:          キャラクターレコード
    form:            形態
    rough_results:   Stage 3 の結果 (generate_rough_images の返却値)
    char_spec:       Stage 2 で構築したキャラクタースペック
    prompts:         Stage 1 の精錬プロンプト dict
    pipeline_dir:    パイプライン出力ルートディレクトリ
    work_key:        作品キー
    correction_mode: 重度違反時の対処モード
                     "t2i"    — Stage 4 内で T2I フル再生成 (デフォルト)
                     "stage3" — Stage 3 に差し戻し (image_pipeline が再生成)
    inputs:          依頼者が渡した入力画像 (src/pipeline/input_images.py)。検査に渡すのは赤入れだけ。

    Returns
    -------
    {
        "corrected":   list[Path]  — 修正が適用された画像
        "passed":      list[Path]  — 違反なし/スキップで通過した画像
        "needs_regen": list[Path]  — Stage 3 差し戻し対象 (stage3 モード時のみ)
        "all":         list[Path]  — corrected + passed (Stage 5 への入力)
    }
    """
    stage_dir = pipeline_dir / "stage4_correct"
    stage_dir.mkdir(parents=True, exist_ok=True)

    # Gemini ラフ + OpenAI ラフ（gpt-image-1 ハイブリッド生成分）を補正対象に合算する。
    # SDXL アタリ ("sdxl_guide") と Adobe 構図ガイド ("adobe_guide") は「Gemini への構図参照(下敷き)」で
    # あり個体正確な最終画ではないため、Stage4 の補正ベースには含めない（"all" も使わない）。
    rough_paths: list[Path] = (
        list(rough_results.get("gemini") or []) +
        list(rough_results.get("openai") or [])
    )
    if not rough_paths:
        print("[Stage4] ラフ画像がありません。Stage 4 をスキップします。")
        return {"corrected": [], "passed": [], "needs_regen": [], "all": []}

    corrected: list[Path] = []
    passed: list[Path] = []
    inspected_passed: list[Path] = []
    needs_regen: list[Path] = []
    analysis_log: list[dict] = []

    # 左右整合チェック用に、公式 DB 参照画像 (Stage 1 の ref_locals) の先頭 1 枚を分析へ添付する。
    # i2i 起点画像 (LoRA 参照や前回 run) 由来の左右反転を原典比較で検出するため。
    ref_image_path: Path | None = None
    for _ref in (prompts.get("ref_locals") or []):
        _ref_path = Path(_ref)
        if _ref_path.exists():
            ref_image_path = _ref_path
            break
    if ref_image_path:
        print(f"[Stage4] 左右整合チェック用の原典参照: {ref_image_path.name}")

    from src.pipeline import input_images
    markup_path: Path | None = next(
        (Path(image["path"]) for image in input_images.for_stage(inputs, 4) if image["kind"] == "markup"), None)
    if markup_path:
        print(f"[Stage4] 赤入れの確認あり: {markup_path.name}")

    for i, rough_path in enumerate(rough_paths, 1):
        if not rough_path.exists():
            print(f"[Stage4] rough_{i:02d}: ファイルが見つかりません。スキップ。")
            continue

        print(f"[Stage4] ({i}/{len(rough_paths)}) {rough_path.name} を分析中...")
        analysis = _analyze_rough_with_openai(
            rough_path, char_spec, ref_image_path=ref_image_path, markup_path=markup_path)

        violations = analysis.get("violations") or []
        missing = analysis.get("missing") or []
        comp_issues = analysis.get("composition_issues") or []
        overall_ok = analysis.get("overall_ok", True)
        skipped = analysis.get("skipped", False)
        corrected_paths: list[Path] = []
        is_stage3_regen = False

        if skipped:
            print(f"[Stage4] rough_{i:02d}: 分析スキップ (API未設定) → pass-through")
            passed.append(rough_path)
        elif overall_ok and not violations and not missing and not comp_issues:
            print(f"[Stage4] rough_{i:02d}: 違反なし → pass-through")
            passed.append(rough_path)
            inspected_passed.append(rough_path)
        else:
            issues = violations + [f"欠落: {m}" for m in missing] + comp_issues
            is_severe = len(violations) >= _SEVERE_VIOLATION_THRESHOLD
            is_stage3_regen = is_severe and correction_mode == "stage3"
            use_t2i = is_severe and correction_mode == "t2i"

            if is_stage3_regen:
                print(
                    f"[Stage4] rough_{i:02d}: 違反 {len(violations)} 件"
                    f" → Stage 3 差し戻し予約 (correction_mode=stage3)"
                )
                needs_regen.append(rough_path)
            else:
                openai_correction_ready = (
                    os.environ.get("OPENAI_CORRECTION_MODEL", "").startswith("gpt-image")
                    and bool(os.environ.get("OPENAI_API_KEY"))
                )
                if use_t2i:
                    mode_label = "T2I/Gemini (形態リセット)"
                elif openai_correction_ready:
                    mode_label = "i2i/OpenAI (外科的修正) → Gemini fallback"
                else:
                    mode_label = "i2i/Gemini (部分修正)"
                print(
                    f"[Stage4] rough_{i:02d}: 違反 {len(violations)}件・欠落 {len(missing)}件"
                    f"・構図問題 {len(comp_issues)}件 → {mode_label}"
                )
                for issue in issues[:5]:
                    print(f"           - {issue}")

                if use_t2i:
                    corrected_paths = _apply_correction_gemini(
                        record, form, rough_path=rough_path, analysis=analysis,
                        prompts=prompts, stage_dir=stage_dir, work_key=work_key,
                        index=i, use_t2i=True,
                    )
                else:
                    corrected_paths = _apply_correction_openai(
                        record, form, rough_path=rough_path, analysis=analysis,
                        stage_dir=stage_dir, work_key=work_key, index=i,
                    )
                    if not corrected_paths:
                        print(f"[INFO] Stage4 rough_{i:02d}: OpenAI 修正なし → Gemini i2i にフォールバック")
                        corrected_paths = _apply_correction_gemini(
                            record, form, rough_path=rough_path, analysis=analysis,
                            prompts=prompts, stage_dir=stage_dir, work_key=work_key,
                            index=i, use_t2i=False,
                        )

                if corrected_paths:
                    corrected.extend(corrected_paths)
                    for corrected_path in corrected_paths:
                        if not corrected_path.exists():
                            continue
                        recheck = _analyze_rough_with_openai(
                            corrected_path, char_spec, ref_image_path=ref_image_path, markup_path=markup_path)
                        recheck_ok = (
                            recheck.get("overall_ok", False)
                            and not recheck.get("violations")
                            and not recheck.get("missing")
                            and not recheck.get("composition_issues")
                            and not recheck.get("skipped")
                        )
                        if recheck_ok:
                            inspected_passed.append(corrected_path)
                            print(f"[Stage4] {corrected_path.name}: 修正後再検査通過")
                        else:
                            print(f"[Stage4] {corrected_path.name}: 修正後再検査で未通過")
                else:
                    print(f"[WARN] Stage4 rough_{i:02d}: 修正失敗 → 元ラフを pass-through")
                    passed.append(rough_path)

        analysis_log.append({
            "rough_index": i,
            "file": rough_path.name,
            "violations": violations,
            "missing": missing,
            "composition_issues": comp_issues,
            "overall_ok": overall_ok,
            "skipped": skipped,
            "corrected": bool(corrected_paths),
            "stage3_regen": is_stage3_regen,
        })

    _save_analysis_log(stage_dir, analysis_log)

    all_paths = corrected + passed
    regen_count = len(needs_regen)
    print(
        f"[Stage4] done - 修正: {len(corrected)} / 通過: {len(passed)}"
        + (f" / Stage3差し戻し: {regen_count}" if regen_count else "")
        + f" / total: {len(all_paths)}"
    )
    return {
        "corrected": corrected,
        "passed": passed,
        "inspected_passed": inspected_passed,
        "needs_regen": needs_regen,
        "all": all_paths,
    }


def _save_analysis_log(stage_dir: Path, log: list[dict]) -> None:
    (stage_dir / "analysis_log.json").write_text(
        json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8"
    )
