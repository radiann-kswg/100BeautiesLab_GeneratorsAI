"""一時調査用: ai_hints.common の実値スキーマを表示する。"""
import json
import sys

from src.utils.dataset import find_character


def main(num: int) -> int:
    rec = find_character(num)
    if rec is None:
        print(f"[ERR] #{num} not found")
        return 1
    hints = rec.get("ai_hints") or {}
    common = hints.get("common") or {}
    print(json.dumps(common, ensure_ascii=False, indent=2)[:3000])
    print("\n--- TYPES ---")
    for k, v in common.items():
        print(f"  {k}: {type(v).__name__}")
    return 0


if __name__ == "__main__":
    sys.exit(main(int(sys.argv[1]) if len(sys.argv) > 1 else 15))
