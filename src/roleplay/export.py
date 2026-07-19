"""
roleplay/export.py — 生成済みロールプレイプロンプトのエクスポート CLI
Copyright © RadianN_kswg — CC BY-NC 4.0

上流 ``build-roleplay-prompts.mjs`` が生成した ``roleplay_prompt.md`` を、
**組み立て直さずゲート付きで消費するだけ**。本文は run_meta に残さない。

使用方法:
    # 生成済みロールプレイプロンプトを取得して output/ に保存 + 標準出力
    python -m src.roleplay.export --num 57

    # 人手先行ワークフロー用に _ideas/roleplay/ にも保存
    python -m src.roleplay.export --num 57 --to-ideas

    # ロールプレイプロンプトを持つ (かつ権利上許可された) キャラ一覧
    python -m src.roleplay.export --list

保存先:
    output/{YYYYMMDD}/{ts}_roleplay_any_num{N}/roleplay_prompt.md  — 本文
    output/{YYYYMMDD}/{ts}_roleplay_any_num{N}/run_meta.json       — メタ (本文なし)
    _ideas/roleplay/num{N}.md                                     — --to-ideas 指定時
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.utils import build_run_output_dir, format_num  # noqa: E402
from src.utils.dataset import _num_matches, load_manifest  # noqa: E402
from src.utils.run_log import write_prompt_file, write_run_meta  # noqa: E402
from src.roleplay.resolve import load_roleplay_prompt  # noqa: E402

DEFAULT_WORK_KEY = "#Works_NumberTales"


def _find_record_for_roleplay(num: int | str, work_key: str = DEFAULT_WORK_KEY):
    """manifest を直接引いてレコードを返す。

    ``get_characters()`` の ``has_ai_hints`` フィルタに依存しない。ロールプレイは
    has_ai_hints 非依存で、manifest の ``ai_training`` / ``roleplay_prompt`` を
    そのまま保持したいため（フィルタを通すとゲート判定に必要な ai_training が落ちる）。
    """
    for r in load_manifest():
        if r.get("_type") != "character":
            continue
        if r.get("work_key") != work_key:
            continue
        if _num_matches((r.get("data") or {}).get("Num"), num):
            return r
    return None


def _iter_available(work_key: str):
    """``has_roleplay_prompt`` を持つレコードを (work, num, status) で列挙する。"""
    for r in load_manifest():
        if r.get("_type") != "character" or not r.get("has_roleplay_prompt"):
            continue
        if work_key and r.get("work_key") != work_key:
            continue
        num = (r.get("data") or {}).get("Num")
        info = load_roleplay_prompt(r, num=num)
        yield r.get("work_key"), num, info["status"]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="生成済みロールプレイプロンプトをゲート付きでエクスポートする（消費のみ）"
    )
    parser.add_argument("--num", help="キャラクター番号 (例: 57)")
    parser.add_argument("--work", default=DEFAULT_WORK_KEY, help="作品キー (既定: #Works_NumberTales)")
    parser.add_argument("--to-ideas", action="store_true", help="_ideas/roleplay/ にも保存する")
    parser.add_argument("--out", default=None, help="出力ベースディレクトリの上書き")
    parser.add_argument(
        "--all-works", action="store_true",
        help="--list 時に全作品を対象にする (既定は --work のみ)",
    )
    parser.add_argument("--list", action="store_true", help="ロールプレイプロンプトを持つキャラ一覧")
    args = parser.parse_args()

    if args.list:
        work_filter = "" if args.all_works else args.work
        rows = list(_iter_available(work_filter))
        ok = [r for r in rows if r[2] == "ok"]
        scope = "全作品" if args.all_works else args.work
        print(f"[roleplay] {scope}: has_roleplay_prompt {len(rows)} 件 (うち許可={len(ok)} 件)")
        for work, num, status in rows:
            mark = "OK " if status == "ok" else f"-- ({status})"
            print(f"  {mark} {work} #{num}")
        return

    if not args.num:
        parser.error("--num または --list を指定してください")

    num: int | str = args.num
    try:
        num = int(num)
    except ValueError:
        pass  # 特殊 ID (str) はそのまま

    record = _find_record_for_roleplay(num, args.work)
    if record is None:
        sys.exit(f"[ERROR] キャラクター #{num} ({args.work}) が manifest に見つかりません。")

    info = load_roleplay_prompt(record, num=num)
    if info["status"] != "ok":
        # refused / unavailable / error は本文を出さずに終了
        print(f"[roleplay] #{num}: {info['status']} — {info['reason']}")
        code = {"unavailable": 0, "refused": 2, "error": 1}.get(info["status"], 1)
        sys.exit(code)

    text: str = info["text"]

    # output/ 保存（本文は roleplay_prompt.md、run_meta には本文を載せない）
    run_dir = build_run_output_dir(provider="roleplay", num=num, form="any", base_dir=args.out)
    write_prompt_file(run_dir, text, filename="roleplay_prompt.md")
    write_run_meta(run_dir, {
        "provider": "roleplay",
        "mode": "export-consume",
        "num": num,
        "work_key": args.work,
        "source": "creations-db roleplay_prompt (build-roleplay-prompts.mjs)",
        "source_path": info["path"],
        "source_submodule_commit": info["submodule_commit"],
        "ai_training_gate": info["ai_training_gate"],
        "char_count": len(text),
    })
    print(f"[roleplay] #{num}: 保存 -> {run_dir}")

    if args.to_ideas:
        ideas_dir = _PROJECT_ROOT / "_ideas" / "roleplay"
        ideas_dir.mkdir(parents=True, exist_ok=True)
        ideas_path = ideas_dir / f"num{format_num(num)}.md"
        ideas_path.write_text(text, encoding="utf-8")
        print(f"[roleplay] #{num}: _ideas へ保存 -> {ideas_path}")

    # 標準出力にも本文を出す（下流利用）
    print("\n" + "=" * 60)
    print(text)


if __name__ == "__main__":
    main()
