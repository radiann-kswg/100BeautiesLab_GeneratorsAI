"""
tests/test_ai_optout_gate.py — AI 学習/生成オプトアウト軸判別ゲートと
ロールプレイ消費 (src.roleplay) の回帰テスト。

pytest 非依存で書いてあり、どちらでも走る:
    python tests/test_ai_optout_gate.py     # 自己完結ランナー
    python -m pytest tests/                 # pytest を入れている場合

合成レコードでゲート論理を、実 manifest で 57(許可)/不許可レコードの漏洩防止を検証する。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.utils.dataset import (  # noqa: E402
    ai_training_allowed,
    ai_training_axis,
    apply_generation_gate,
    generation_permitted,
)
from src.roleplay.resolve import (  # noqa: E402
    _filename_matches_num,
    load_roleplay_prompt,
    resolve_roleplay_prompt_path,
)

# 上流 policy.js の理由文に対応する合成レコード
_RIGHTS = {"ai_training": {"allowed": False,
           "reason": "AI_Optout: true is set in db_meta.json for this DB. "
                     "This DB is opted out of AI training/generation use."}}
_FILL = {"ai_training": {"allowed": False,
         "reason": 'Progress: "stillTentative" is declared AI_Unready in $EnumDef_Progress '
                   "(creation not advanced enough to provide content, or a secondary-work "
                   "progress state). This is NOT a rights-based opt-out: rights are expressed "
                   "only by AI_Optout."}}
_UNKNOWN = {"ai_training": {"allowed": False, "reason": "some brand new reason not seen before"}}
_ALLOWED = {"ai_training": {"allowed": True, "reason": "opted in"}}


def test_ai_training_allowed():
    assert ai_training_allowed(_ALLOWED) is True
    assert ai_training_allowed(_RIGHTS) is False
    assert ai_training_allowed(_FILL) is False
    assert ai_training_allowed(None) is True          # 欠落は fail-open (列挙側)
    assert ai_training_allowed({}) is True


def test_ai_training_axis():
    assert ai_training_axis(_ALLOWED) == "allowed"
    assert ai_training_axis(_RIGHTS) == "rights"
    assert ai_training_axis(_FILL) == "fill"
    assert ai_training_axis(_UNKNOWN) == "rights"      # 未知理由は保守的に rights(hard)
    assert ai_training_axis(None) == "allowed"


def test_generation_permitted_by_usage():
    # 許可
    for usage in ("image", "text", "roleplay"):
        assert generation_permitted(_ALLOWED, usage=usage)[0] == "allow"
    # 権利軸 → 全用途 refuse
    for usage in ("image", "text", "roleplay"):
        assert generation_permitted(_RIGHTS, usage=usage)[0] == "refuse"
    # 充填軸 → image/text は warn、roleplay は refuse (最厳格)
    assert generation_permitted(_FILL, usage="image")[0] == "warn"
    assert generation_permitted(_FILL, usage="text")[0] == "warn"
    assert generation_permitted(_FILL, usage="roleplay")[0] == "refuse"


def test_kill_switch_disables_gate():
    prev = os.environ.get("AI_OPTOUT_ENFORCE")
    os.environ["AI_OPTOUT_ENFORCE"] = "0"
    try:
        assert generation_permitted(_RIGHTS, usage="roleplay")[0] == "allow"
        assert generation_permitted(_FILL, usage="roleplay")[0] == "allow"
    finally:
        if prev is None:
            os.environ.pop("AI_OPTOUT_ENFORCE", None)
        else:
            os.environ["AI_OPTOUT_ENFORCE"] = prev


def test_apply_generation_gate_meta():
    proceed, gate = apply_generation_gate(_RIGHTS, usage="image", num=999, printer=None)
    assert proceed is False
    assert gate["decision"] == "refuse" and gate["axis"] == "rights" and gate["skipped"] is True
    proceed, gate = apply_generation_gate(_FILL, usage="image", num=999, printer=None)
    assert proceed is True and gate["decision"] == "warn" and gate["skipped"] is False
    proceed, gate = apply_generation_gate(_ALLOWED, usage="image", num=999, printer=None)
    assert proceed is True and gate["decision"] == "allow"


def test_filename_matches_num():
    p = Path("data/Works_NumberTales/RoleplayPrompts/DB_Primary/roleplay-prompt-57.md")
    assert _filename_matches_num(p, 57) is True
    assert _filename_matches_num(p, "57") is True
    assert _filename_matches_num(p, 58) is False
    assert _filename_matches_num(Path("something-else.md"), 57) is False


def test_resolve_path_traversal_guard():
    ok = {"roleplay_prompt": {"path":
          "data/Works_NumberTales/RoleplayPrompts/DB_Primary/roleplay-prompt-57.md"}}
    assert resolve_roleplay_prompt_path(ok) is not None
    # RoleplayPrompts 配下以外は拒否
    outside = {"roleplay_prompt": {"path":
               "data/Works_NumberTales/DataBases/db_Primary.json"}}
    assert resolve_roleplay_prompt_path(outside) is None
    # ../ でルート外へ出るパスは拒否
    traversal = {"roleplay_prompt": {"path": "../../../etc/passwd"}}
    assert resolve_roleplay_prompt_path(traversal) is None
    # path 無し
    assert resolve_roleplay_prompt_path({}) is None


def test_load_roleplay_refused_and_unavailable():
    # 権利軸/充填軸オプトアウト → refused、本文は読まない
    rec = dict(_RIGHTS)
    rec["has_roleplay_prompt"] = True
    rec["roleplay_prompt"] = {"path":
        "data/Works_NumberTales/RoleplayPrompts/DB_Primary/roleplay-prompt-57.md"}
    info = load_roleplay_prompt(rec, num=57)
    assert info["status"] == "refused" and info["text"] is None
    # 許可だが生成物なし → unavailable
    info2 = load_roleplay_prompt(dict(_ALLOWED), num=57)
    assert info2["status"] == "unavailable" and info2["text"] is None


def test_load_roleplay_ok_integration():
    """実 manifest の 57 が許可され本文が読める (submodule 前提。無ければ skip)。"""
    try:
        from src.utils.dataset import load_manifest, _num_matches
    except Exception:
        return
    try:
        records = load_manifest()
    except Exception:
        return  # manifest 未配置環境では skip
    rec = next((r for r in records
                if r.get("_type") == "character"
                and r.get("work_key") == "#Works_NumberTales"
                and _num_matches((r.get("data") or {}).get("Num"), 57)), None)
    if rec is None or not rec.get("has_roleplay_prompt"):
        return
    info = load_roleplay_prompt(rec, num=57)
    assert info["status"] == "ok"
    assert info["text"] and "57(イズナ)" in info["text"]


def _run() -> int:
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_run())
