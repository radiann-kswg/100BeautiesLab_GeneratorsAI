"""
tests/test_badge_reference_images.py — インデックスバッジ命名 (2026-08-02 上流一括改名) に
追従した参照画像フィルタの回帰テスト。

pytest 非依存で書いてあり、どちらでも走る:
    python tests/test_badge_reference_images.py   # 自己完結ランナー
    python -m pytest tests/                       # pytest を入れている場合

上流 creations-db が画像ファイル名を `{prefix}_{kind}{Works_Code}-{バッジ本体}{接尾辞}` へ
一括改名した (`cnsp_img57.png` → `cnsp_imgNTS-57.png`、`cnsp_img2-alt.png` → `cnsp_imgNTS-2B.png`)。
番号の部分一致を前提にしていた旧フィルタは、この命名で次の破綻を起こしていた:

  - `Num:"2-alt"` (バッジ `2B`) がファイル名に "2-alt" を含まず参照画像を全て失う
  - `Num:2` の部分一致が `NTS-2B` や接尾辞 `-2` (`NTS-10-2` 等) を拾い他キャラが混入する
  - `Num:67` と `Num:"67-old"` がバッジ `67A` / `67B` に分かれ互いの画像を取り違える

語彙との最長前方一致で切り出すのが要点 (`NTS-2B` は `2` ではなく `2B`、`NTS-57RZ` は `57`)。
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.utils.dataset import (  # noqa: E402
    _badge_tokens_in_filename,
    _extract_record_badge,
    _load_badge_vocabulary,
    _load_works_code,
    _looks_like_target_character,
    collect_reference_images,
    find_character,
    get_characters,
)

_WORK = "#Works_NumberTales"
_DB_BASE = "_creations-ai/creations-db"

# 実データに依存しない合成語彙 (長い順に並べるのは呼び出し側ではなく関数側の責務ではないため、
# `_load_badge_vocabulary` と同じ「長い順」を明示的に作って渡す)。
_VOCAB = tuple(sorted(
    {"0", "00", "000", "1", "2", "2B", "10", "10D", "12", "57", "65", "56", "67", "67A", "67B", "97"},
    key=lambda b: (-len(b), b),
))


def _submodule_ready() -> bool:
    """creations-db サブモジュールと manifest が揃っているか (未配置環境では skip)。"""
    try:
        return bool(_load_works_code(_WORK, _DB_BASE)) and bool(_load_badge_vocabulary(_WORK))
    except Exception:  # noqa: BLE001
        return False


# ── バッジ切り出し (最長前方一致) ─────────────────────────────────────────────

def test_badge_tokens_longest_prefix_match():
    """`NTS-2B` は `2` ではなく `2B` に解決する (取り違えると 2 と 2-alt が混ざる)。"""
    assert _badge_tokens_in_filename("cnsp_imgNTS-2B.png", "NTS", _VOCAB) == {"2B"}
    assert _badge_tokens_in_filename("cnsp_imgNTS-2.png", "NTS", _VOCAB) == {"2"}
    assert _badge_tokens_in_filename("attr_numberMarkNTS-10D.png", "NTS", _VOCAB) == {"10D"}
    assert _badge_tokens_in_filename("cnsp_imgNTS-67A.png", "NTS", _VOCAB) == {"67A"}
    assert _badge_tokens_in_filename("cnsp_imgNTS-67B.png", "NTS", _VOCAB) == {"67B"}
    # 000 / 00 / 0 は長い順に評価しないと 0 へ潰れる
    assert _badge_tokens_in_filename("emstk_corefolderNTS-000-2.png", "NTS", _VOCAB) == {"000"}


def test_badge_tokens_ignore_suffix():
    """接尾辞はバッジではない。`-1` / `-2` の連番や `RZ` / `MP` を番号と誤認しない。"""
    # 旧フィルタは Num:2 がこの `-2` を拾って他キャラを混入させていた
    assert _badge_tokens_in_filename("emstk_corefolderNTS-10-2.png", "NTS", _VOCAB) == {"10"}
    assert _badge_tokens_in_filename("emstk_corefolderNTS-1-2.png", "NTS", _VOCAB) == {"1"}
    assert _badge_tokens_in_filename("attr_numberMarkNTS-97-2.png", "NTS", _VOCAB) == {"97"}
    # RZ (旧 -numberize) / MP (旧 -mp) は接尾辞なので本体バッジへ寄せる
    assert _badge_tokens_in_filename("cnsp_imgNTS-57RZ.png", "NTS", _VOCAB) == {"57"}
    assert _badge_tokens_in_filename("cnsp_imgNTS-57MP.png", "NTS", _VOCAB) == {"57"}


def test_badge_tokens_joint_filename():
    """連名 (`NTS-56,NTS-65`) は両方のバッジを返す。"""
    got = _badge_tokens_in_filename("art_imgNTS-56,NTS-65-corefolderA.png", "NTS", _VOCAB)
    assert got == {"56", "65"}


def test_badge_tokens_absent():
    """バッジ命名を持たないファイル名 (イベント年月ベース) は空集合。"""
    assert _badge_tokens_in_filename("art_numbertalesAniv2nd.png", "NTS", _VOCAB) == set()
    assert _badge_tokens_in_filename("art_sphericateDay202112.png", "NTS", _VOCAB) == set()
    # 作品コード不明・語彙なしでも例外にせず空集合
    assert _badge_tokens_in_filename("cnsp_imgNTS-57.png", "", _VOCAB) == set()
    assert _badge_tokens_in_filename("cnsp_imgNTS-57.png", "NTS", ()) == set()


# ── require_badge によるフォールバック制御 ───────────────────────────────────

def test_require_badge_drops_unidentifiable_paths():
    """総当たり収集 (require_badge=True) はバッジで同定できないパスを採らない。

    DB 由来 (require_badge=False) は旧命名の部分一致へフォールバックして後方互換を保つ。
    """
    if not _submodule_ready():
        return
    path = "data/Works_NumberTales/Images/DB_Primary/arts/humanoids/art_numbertalesAniv2nd.png"
    common = dict(badge="2", work_key=_WORK, creations_db_base=_DB_BASE)
    # 旧ロジックなら "2" が "Aniv2nd" にマッチしてしまう位置づけのパス
    assert _looks_like_target_character(path, 2, require_badge=True, **common) is False
    assert _looks_like_target_character(path, 2, require_badge=False, **common) is True


def test_badge_match_beats_number_substring():
    """バッジを解決できたパスは厳密一致で判定し、番号の部分一致に引きずられない。"""
    if not _submodule_ready():
        return
    path = "data/Works_NumberTales/Images/DB_Primary/concept/cnsp_imgNTS-2B.png"
    # Num:2 (ツグ) から見れば 2-alt(バイナ) の画像なので採ってはいけない
    assert _looks_like_target_character(
        path, 2, badge="2", work_key=_WORK, creations_db_base=_DB_BASE) is False
    # Num:"2-alt" から見れば本人の画像。旧ロジックでは "2-alt" を含まず失われていた
    assert _looks_like_target_character(
        path, "2-alt", badge="2B", work_key=_WORK, creations_db_base=_DB_BASE) is True


# ── レコードからのバッジ導出 ─────────────────────────────────────────────────

def test_extract_record_badge_prefers_num_badge():
    """`$IndexDef.$badge` の `whenMissing` 宣言どおり Num_Badge 優先・無ければ Num。"""
    assert _extract_record_badge({"data": {"Num": "2-alt", "Num_Badge": "2B"}}) == "2B"
    assert _extract_record_badge({"data": {"Num": 57}}) == "57"
    assert _extract_record_badge({"db_record": {"Num": 57, "Num_Badge": "57"}}) == "57"
    assert _extract_record_badge({"data": {}}) == ""
    assert _extract_record_badge({}) == ""


def test_real_record_badges():
    """実 manifest のバッジ対応 (submodule 前提。無ければ skip)。"""
    if not _submodule_ready():
        return
    expected = {57: "57", 2: "2", "2-alt": "2B", "10-alt": "10D", 67: "67A", "67-old": "67B"}
    for num, badge in expected.items():
        rec = find_character(num)
        assert rec is not None, f"num={num!r} が見つからない"
        assert _extract_record_badge(rec) == badge, f"num={num!r} のバッジが {badge} でない"


# ── 参照画像の統合回帰 ───────────────────────────────────────────────────────

def test_alt_characters_resolve_reference_images():
    """特殊 ID のキャラが参照画像を失わない (改名前は humanoid が 0 件だった)。"""
    if not _submodule_ready():
        return
    for num in ("2-alt", "10-alt", "67-old"):
        rec = find_character(num)
        assert rec is not None, f"num={num!r} が見つからない"
        found = {
            form: collect_reference_images(rec, form=form, creations_db_base=_DB_BASE)["local_paths"]
            for form in ("corefolder", "humanoid")
        }
        assert any(found.values()), f"num={num!r} の参照画像が全形態で 0 件"


def test_no_cross_character_contamination():
    """全キャラの参照画像に、自分以外のバッジだけを持つパスが混ざらない。

    改名直後は 471 件中 32 件が他キャラの画像だった (`NTS-10-2` の接尾辞を Num:2 が拾う等)。
    """
    if not _submodule_ready():
        return
    code = _load_works_code(_WORK, _DB_BASE)
    vocab = _load_badge_vocabulary(_WORK)
    offenders: list[str] = []
    for rec in get_characters():
        if rec.get("work_key") != _WORK:
            continue
        badge = _extract_record_badge(rec)
        if not badge:
            continue
        for form in ("corefolder", "humanoid"):
            for path in collect_reference_images(
                rec, form=form, creations_db_base=_DB_BASE
            )["local_paths"]:
                tokens = _badge_tokens_in_filename(path, code, vocab)
                if tokens and badge not in tokens:
                    offenders.append(f"badge={badge} {form}: {Path(path).name} -> {sorted(tokens)}")
    assert not offenders, "他キャラの画像が混入: " + "; ".join(offenders[:10])


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
