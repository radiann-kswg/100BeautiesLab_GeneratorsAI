"""課金なし: 別衣装の記述を生成に混ぜず、AI に渡さない衣装と画像を外す。"""
from src.utils import dataset


def costume_record():
    def entry(costume, text, element="#Element_CostumeItem"):
        return {"Formation": "humanoid", "Costume": costume, "DesignElement": element,
                "Attrs": [{"AttrLabel": "#DesignAttr_Overview", "value_EN": text},
                          {"AttrLabel": "#DesignAttr_Color", "value_EN": "dark"}]}
    tags = ["pink vest (usual outfit)", "red uniform (idol outfit)", "On both shoulders (idol outfit), dark",
            "long ponytail"]
    return {
        "work_key": "#Works_NumberTales",
        "data": {"Num": 61, "AppearanceDetail": [
            entry("usual", "pink vest (usual outfit)"),
            entry("idol", "red uniform (idol outfit)"),
            entry("idol", "On both shoulders (idol outfit)", "#Element_NumberMark"),
            entry(None, "long ponytail"),
        ]},
        "ai_hints": {
            "common": {"identity_tags": list(tags),
                       "immutable_traits": ["number '61' marking: On both shoulders (idol outfit), dark"]},
            "forms": {"humanoid": {"ai_tags": list(tags), "prompt_export": ", ".join(tags)}},
        },
        "images": {"corefolder": ["a/emstk_corefolderNTS-61-1.png", "a/emstk_corefolderNTS-61-idol1.png"],
                   "design_alt": [{"path": "a/chr-dsgn-alt_wipNTS-61-idol.png", "form": None}]},
        "preferred_reference_images": {"common": {"concept": "a/cnsp_imgNTS-61.png",
                                                  "design_sheet": "a/chr-dsgn-alt_wipNTS-61-idol.png"}},
    }


def test_other_costumes_are_dropped_from_details_and_hints():
    record = costume_record()
    result = dataset.drop_costumes(record, lambda costume: costume != "usual")

    assert [e["Costume"] for e in result["data"]["AppearanceDetail"]] == ["usual", None]
    hints = result["ai_hints"]
    assert hints["common"]["identity_tags"] == ["pink vest (usual outfit)", "long ponytail"]
    assert hints["common"]["immutable_traits"] == []
    assert hints["forms"]["humanoid"]["ai_tags"] == ["pink vest (usual outfit)", "long ponytail"]
    # つないだ文は空にして、generation_ai_hints() に ai_tags から組み直させる
    assert hints["forms"]["humanoid"]["prompt_export"] == ""
    assert "idol" not in dataset.generation_ai_hints(result)["forms"]["humanoid"]["prompt_export"]
    # 元のレコードは変えない。残す項目と共通の文面（"dark"）では照合しない
    assert len(record["data"]["AppearanceDetail"]) == 4
    assert "red uniform (idol outfit)" in record["ai_hints"]["common"]["identity_tags"]


def test_record_without_costume_tags_is_returned_as_is():
    record = {"data": {"AppearanceDetail": [{"Formation": "humanoid", "Attrs": []}]}}
    assert dataset.drop_costumes(record, lambda costume: True) is record


def test_rights_excluded_costume_and_images_are_stripped_on_load():
    record = costume_record()
    result = dataset._strip_ai_excluded(record, "chr-dsgn-alt_wipNTS-61-idol emstk_corefolderNTS-61-idol1")

    assert [e["Costume"] for e in result["data"]["AppearanceDetail"]] == ["usual", None]
    assert result["images"] == {"corefolder": ["a/emstk_corefolderNTS-61-1.png"], "design_alt": []}
    assert result["preferred_reference_images"] == {"common": {"concept": "a/cnsp_imgNTS-61.png"}}
    # ほかの作品の同名の衣装は、権利上の除外の対象にしない
    other = dataset._strip_ai_excluded(dict(record, work_key="#Works_Other"))
    assert len(other["data"]["AppearanceDetail"]) == 4


def test_excluded_image_is_recognised_in_any_spelling():
    assert dataset.is_ai_excluded_image("data/x/corefolder/61/emstk_corefolderNTS-61-idol2.png")
    assert dataset.is_ai_excluded_image("catalog\\chr-dsgn-alt_wipNTS-61-idol")
    assert not dataset.is_ai_excluded_image("data/x/corefolder/61/emstk_corefolderNTS-61-1.png")
    assert not dataset.is_ai_excluded_image(None)
