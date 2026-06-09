"""A5 dry-run プロンプト確認: 重点要素ブロックと NLD を 6 キャラ分抽出"""
from src.utils.dataset import find_character, build_gemini_prompt

for num in [7, 22, 42, 57, 73, 96]:
    rec = find_character(num)
    result = build_gemini_prompt(rec, form="corefolder", scene="")
    prompt = result["prompt"]
    print(f"========== #{num} ==========")
    s = prompt.find("[今回の姿]"); e = prompt.find("[形態固定ルール]")
    print(prompt[s:e].rstrip())
    print()
    s2 = prompt.find("[現在形態の重点要素]"); e2 = prompt.find("[混入禁止")
    if s2 >= 0:
        print(prompt[s2:e2].rstrip())
    else:
        print("(no focus block)")
    print()
