"""--badge 引数: DB の Num_Badge からレコードを解決できることの回帰テスト (課金なし)。"""
from src.utils.dataset import find_character, get_characters, resolve_badge

_WORK = "#Works_NumberTales"


def test_resolve_badge_maps_to_record_num():
    assert resolve_badge(57) == 57
    assert resolve_badge("57") == 57
    assert resolve_badge("2B") == "2-alt"       # バイナ (Num:"2-alt", Num_Badge:"2B")
    assert resolve_badge("2b") == "2-alt"       # 大文字小文字は区別しない
    assert resolve_badge("67B") == "67-old"
    assert resolve_badge("2-alt") == "2-alt"    # 旧来の特殊 ID はそのまま通す
    assert resolve_badge("バイナ") == "バイナ"   # 名前解決は image_pipeline 側の責務


def test_every_record_is_reachable_by_its_badge():
    for rec in get_characters():
        if rec.get("work_key") != _WORK:
            continue
        badge = rec["data"].get("Num_Badge")
        assert badge, rec["data"].get("Num")
        if str(badge).isdigit():
            continue  # 数字のみは従来の Num 照合経路 ("0" と "000" の int 一致は既存仕様)
        found = find_character(badge, _WORK)
        assert found is not None and str(found["data"]["Num"]) == str(rec["data"]["Num"]), badge


def test_find_character_badge_does_not_collide_with_plain_num():
    assert find_character(2, _WORK)["data"]["Num"] == 2          # ツグ
    assert find_character("2B", _WORK)["data"]["Num"] == "2-alt"  # バイナ
