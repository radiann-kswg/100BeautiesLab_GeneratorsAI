"""複数キャラクター・形態を一括で生成するバッチランチャー。

例::

    # gemini で #15, #22, #57 の corefolder/humanoid を順番に試す
    python -m src.batch_generate --nums 15,22,57 --provider gemini --forms both

    # openai (gpt-image-1) で #49 と #57 を corefolder のみ
    python -m src.batch_generate --nums 49,57 --provider openai --forms corefolder

    # 両方のプロバイダで同じシーン指定
    python -m src.batch_generate --nums 22,49,57 --provider both --forms both \
        --scene "夕暮れの研究所のテラスで主人とお茶している場面"

特徴:
  - 1キャラ/形態が失敗しても次へ進む。最終にサマリー表示。
  - 各実行は通常通り 3 階層レイアウト
    ``output/{YYYYMMDD}/{YYYYMMDD_HH}/{ts}_{provider}_{form}_num{NNN}/`` に出力
    (生成は ``src/utils/paths.py`` の ``build_run_output_dir()``)。
  - 形態フィルタ (B拡張): humanoid を指定したキャラクターでも、
    そのキャラクターに humanoid 形態の AI ヒントが無い場合は警告して skip する
    (``--skip-no-hints`` がデフォルト ON)。
"""
from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

# プロジェクトルートを sys.path に追加
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.utils import (  # noqa: E402
    apply_generation_gate,
    collect_record_capabilities,
    find_character,
)


@dataclass
class BatchResult:
    num: int
    form: str
    provider: str
    status: str  # "ok" / "skipped" / "failed"
    detail: str = ""
    output_paths: list[str] = field(default_factory=list)


def _parse_int_list(text: str) -> list[int]:
    """`"22,49,57"` のようなカンマ区切り文字列を整数リストに変換。"""
    out: list[int] = []
    for token in text.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            out.append(int(token))
        except ValueError:
            raise SystemExit(f"[ERROR] --nums の値 '{token}' は整数として解釈できません。")
    if not out:
        raise SystemExit("[ERROR] --nums に少なくとも1つの番号を指定してください。")
    return out


def _expand_forms(form_arg: str) -> list[str]:
    if form_arg == "both":
        return ["corefolder", "humanoid"]
    return [form_arg]


def _expand_providers(provider_arg: str) -> list[str]:
    if provider_arg == "both":
        return ["gemini", "openai"]
    if provider_arg == "all":
        # canva は入力画像 (--from-image) が必須なためバッチ一括には含めない。
        return ["gemini", "openai", "adobe"]
    return [provider_arg]


def _run_one(
    provider: str,
    num: int,
    form: str,
    work_key: str,
    out_dir: str | None,
    count: int,
    scene: str,
    size: str,
    style: str = "",
    composition: str = "",
    background: str = "",
) -> BatchResult:
    """1キャラクター・1形態・1プロバイダを実行する。"""
    if provider == "gemini":
        from src.gemini.generate import generate_image as gemini_generate

        try:
            paths = gemini_generate(
                num=num,
                form=form,
                work_key=work_key,
                out_dir=out_dir,
                count=count,
                scene=scene,
                style=style,
                composition=composition,
                background=background,
            )
        except SystemExit as e:
            return BatchResult(num, form, provider, "failed", f"SystemExit: {e}")
        except Exception as e:
            return BatchResult(num, form, provider, "failed", f"{type(e).__name__}: {e}")

        if not paths:
            return BatchResult(num, form, provider, "failed", "no images generated")
        return BatchResult(
            num, form, provider, "ok", f"{len(paths)} png", [str(p) for p in paths]
        )

    if provider == "openai":
        from src.openai.generate import generate_image_dalle as openai_generate

        try:
            path = openai_generate(
                num=num,
                form=form,
                work_key=work_key,
                out_dir=out_dir,
                size=size,
                scene=scene,
                style=style,
                composition=composition,
                background=background,
            )
        except SystemExit as e:
            return BatchResult(num, form, provider, "failed", f"SystemExit: {e}")
        except Exception as e:
            return BatchResult(num, form, provider, "failed", f"{type(e).__name__}: {e}")

        if path is None:
            return BatchResult(num, form, provider, "failed", "no image generated")
        return BatchResult(num, form, provider, "ok", "1 png", [str(path)])

    if provider == "adobe":
        from src.adobe.generate import generate_image_firefly as firefly_generate

        try:
            paths = firefly_generate(
                num=num,
                form=form,
                work_key=work_key,
                out_dir=out_dir,
                count=count,
                scene=scene,
                style=style,
                composition=composition,
                background=background,
            )
        except SystemExit as e:
            return BatchResult(num, form, provider, "failed", f"SystemExit: {e}")
        except Exception as e:
            return BatchResult(num, form, provider, "failed", f"{type(e).__name__}: {e}")

        if not paths:
            return BatchResult(num, form, provider, "failed", "no images generated")
        return BatchResult(
            num, form, provider, "ok", f"{len(paths)} img", [str(p) for p in paths]
        )

    if provider == "canva":
        # Canva は生成済み画像が必要。バッチ一括では扱わず単発実行へ誘導する。
        return BatchResult(
            num, form, provider, "skipped",
            "canva は --from-image が必須: python -m src.canva.generate --num N --from-image <path>",
        )

    return BatchResult(num, form, provider, "failed", f"unknown provider: {provider}")


def run_batch(
    nums: list[int],
    forms: list[str],
    providers: list[str],
    work_key: str = "#Works_NumberTales",
    out_dir: str | None = None,
    count: int = 1,
    scene: str = "",
    size: str = "1024x1024",
    skip_no_hints: bool = True,
    sleep_between: float = 0.0,
    dry_run: bool = False,
    style: str = "",
    composition: str = "",
    background: str = "",
) -> list[BatchResult]:
    """指定された組み合わせを順に実行し、結果リストを返す。

    ``dry_run=True`` のときは実 API を一切呼ばず、各組み合わせの予定 (RUN/SKIP) と
    capability だけをログ出力する。
    """
    results: list[BatchResult] = []
    total = len(nums) * len(forms) * len(providers)
    print(f"[BATCH] 実行予定: {total} 件 "
          f"(nums={nums}, forms={forms}, providers={providers})")
    idx = 0
    for num in nums:
        record = find_character(num, work_key)
        if record is None:
            for form in forms:
                for provider in providers:
                    idx += 1
                    print(f"\n[BATCH {idx}/{total}] #{num} {form} {provider} -> NOT_FOUND")
                    results.append(
                        BatchResult(num, form, provider, "skipped", "character not found")
                    )
            continue

        # AI 学習/生成オプトアウト・ゲート（キャラ単位・form 非依存）。
        # 権利軸オプトアウトは全 form×provider を skipped に。充填軸は警告のうえ続行。
        proceed, gate = apply_generation_gate(
            record, usage="image", num=num, printer=print
        )
        if not proceed:
            for form in forms:
                for provider in providers:
                    idx += 1
                    print(f"\n[BATCH {idx}/{total}] #{num} {form} {provider} -> SKIP (ai-optout)")
                    results.append(
                        BatchResult(
                            num, form, provider, "skipped",
                            f"ai_training opt-out: {gate['reason']}",
                        )
                    )
            continue

        for form in forms:
            cap = collect_record_capabilities(record, form=form)
            for provider in providers:
                idx += 1
                header = f"\n[BATCH {idx}/{total}] #{num} {form} {provider}"
                if skip_no_hints and not cap.get("current_form_hints_present"):
                    print(
                        f"{header} -> SKIP (current_form_hints_present=False) "
                        f"forms_available={cap.get('form_hints_available')}"
                    )
                    results.append(
                        BatchResult(
                            num,
                            form,
                            provider,
                            "skipped",
                            "no ai_hints for this form",
                        )
                    )
                    continue
                print(
                    f"{header} -> RUN "
                    f"hints_forms={cap.get('form_hints_available')} "
                    f"outfit({cap.get('outfit_features_count')}->"
                    f"{cap.get('outfit_features_after_filter')}) "
                    f"db_img={cap.get('db_image_present')}"
                )
                if dry_run:
                    print(f"[BATCH {idx}/{total}] -> DRY-RUN (API 未実行)")
                    results.append(
                        BatchResult(num, form, provider, "skipped", "dry-run")
                    )
                    continue
                res = _run_one(
                    provider=provider,
                    num=num,
                    form=form,
                    work_key=work_key,
                    out_dir=out_dir,
                    count=count,
                    scene=scene,
                    size=size,
                    style=style,
                    composition=composition,
                    background=background,
                )
                print(f"[BATCH {idx}/{total}] -> {res.status} {res.detail}")
                results.append(res)
                if sleep_between > 0:
                    time.sleep(sleep_between)
    return results


def _print_summary(results: list[BatchResult]) -> None:
    ok = [r for r in results if r.status == "ok"]
    skipped = [r for r in results if r.status == "skipped"]
    failed = [r for r in results if r.status == "failed"]
    print("\n========== BATCH SUMMARY ==========")
    print(f"total={len(results)} ok={len(ok)} skipped={len(skipped)} failed={len(failed)}")
    if skipped:
        print("\n[skipped]")
        for r in skipped:
            print(f"  - #{r.num} {r.form} {r.provider}: {r.detail}")
    if failed:
        print("\n[failed]")
        for r in failed:
            print(f"  - #{r.num} {r.form} {r.provider}: {r.detail}")
    if ok:
        print("\n[ok]")
        for r in ok:
            print(f"  - #{r.num} {r.form} {r.provider}: {r.detail}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="複数キャラクター・形態を順番に画像生成するバッチランチャー。"
    )
    parser.add_argument(
        "--nums",
        required=True,
        help="カンマ区切りのキャラクター番号 (例: 15,22,49,57)",
    )
    parser.add_argument(
        "--forms",
        choices=["corefolder", "humanoid", "both"],
        default="both",
        help="生成する形態 (デフォルト: both)",
    )
    parser.add_argument(
        "--provider",
        choices=["gemini", "openai", "adobe", "canva", "both", "all"],
        default="gemini",
        help=(
            "使用するプロバイダ (デフォルト: gemini)。"
            " both=gemini+openai / all=gemini+openai+adobe。"
            " canva は --from-image 必須のため単発実行を推奨。"
        ),
    )
    parser.add_argument("--work", default="#Works_NumberTales", help="作品キー")
    parser.add_argument(
        "--out",
        default=None,
        help="出力ベースディレクトリ (省略時は OUTPUT_BASE_DIR / 'output')",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        choices=range(1, 5),
        help="gemini の場合の生成枚数 (1-4)",
    )
    parser.add_argument(
        "--scene",
        default="",
        help="全実行に共通で差し込むシーン/ポーズ説明",
    )
    parser.add_argument(
        "--style",
        default="",
        help="全実行に共通で差し込む作風ヒント (例: 'watercolor')",
    )
    parser.add_argument(
        "--composition",
        default="",
        help="全実行に共通で差し込む構図ヒント (例: 'bust shot')",
    )
    parser.add_argument(
        "--background",
        default="",
        help="全実行に共通で差し込む背景ヒント (例: 'white background')",
    )
    parser.add_argument(
        "--size",
        choices=["1024x1024", "1792x1024", "1024x1792"],
        default="1024x1024",
        help="OpenAI 画像サイズ",
    )
    parser.add_argument(
        "--no-skip-no-hints",
        action="store_true",
        help="ai_hints が無い形態でも強制的に実行する (デフォルトは skip)",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.0,
        help="各実行間のスリープ秒数 (rate-limit 回避用)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="実 API を呼ばずに RUN/SKIP の予定と capability だけを表示。課金は発生しない。",
    )
    args = parser.parse_args()

    nums = _parse_int_list(args.nums)
    forms = _expand_forms(args.forms)
    providers = _expand_providers(args.provider)

    results = run_batch(
        nums=nums,
        forms=forms,
        providers=providers,
        work_key=args.work,
        out_dir=args.out,
        count=args.count,
        scene=args.scene,
        size=args.size,
        skip_no_hints=not args.no_skip_no_hints,
        sleep_between=args.sleep,
        dry_run=args.dry_run,
        style=args.style,
        composition=args.composition,
        background=args.background,
    )
    _print_summary(results)


if __name__ == "__main__":
    main()
