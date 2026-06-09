"""一時トレース用: build_gemini_prompt の TypeError 箇所を特定する."""
import sys
import traceback

from src.utils.dataset import build_gemini_prompt, find_character


def main(num: int, form: str) -> int:
    record = find_character(num)
    if record is None:
        print(f"[ERR] record #{num} not found")
        return 1
    print(f"[INFO] record found: keys={list(record.keys())[:12]}")
    try:
        prompt = build_gemini_prompt(record, form=form)
        print(f"[OK] prompt length={len(prompt)} chars")
        print(prompt[:600])
        return 0
    except Exception:
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    f = sys.argv[2] if len(sys.argv) > 2 else "corefolder"
    sys.exit(main(n, f))
