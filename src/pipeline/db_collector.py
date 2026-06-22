"""
pipeline/db_collector.py — Stage 2: キャラクター選定 + 創作 DB データ取得
Copyright © RadianN_kswg — CC BY-NC 4.0

Stage 1 で確定したキャラクター番号を基に、創作 DB から以下を収集・整理する:
  - キャラクターレコード (manifest.jsonl から)
  - 原典参照画像 (ローカル + URL)
  - 形態別バリデーション用スペック (Stage 4 の違反検出に使用)

結果は stage2_db/ ディレクトリに保存される。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.utils import find_character  # noqa: E402
from src.utils.dataset import collect_reference_images, _filter_immutable_traits_by_form  # noqa: E402


def collect_character_data(
    num: int | str,
    form: str,
    pipeline_dir: Path,
    work_key: str = "#Works_NumberTales",
) -> dict | None:
    """Stage 2: キャラクターを選定し DB から原典画像・特徴を取得する。

    Parameters
    ----------
    num:          キャラクター番号 (整数または文字列 ID e.g. "2-alt")
    form:         形態 ("corefolder" / "humanoid")
    pipeline_dir: パイプライン出力ルートディレクトリ
    work_key:     作品キー

    Returns
    -------
    {
        "record":     dict             — キャラクターレコード
        "references": dict             — {"urls": list[str], "local_paths": list[str]}
        "spec":       dict             — 形態別バリデーション用スペック
    }
    キャラクターが見つからない場合は None を返す。
    """
    stage_dir = pipeline_dir / "stage2_db"
    stage_dir.mkdir(parents=True, exist_ok=True)

    record = find_character(num, work_key)
    if record is None:
        print(f"[Stage2] ERROR: キャラクター #{num} ({work_key}) が見つかりません。")
        return None

    _num_label = f"#{num:03d}" if isinstance(num, int) else f"#{num}"
    char_name = record["data"].get("Name_JP") or record["data"].get("Name") or _num_label
    print(f"[Stage2] キャラクター選定: {char_name} / 形態: {form}")

    references = collect_reference_images(record, form=form)
    spec = _build_character_spec(record, form)

    _save_db_summary(stage_dir, record, form, references, spec)

    ref_total = len(references["urls"]) + len(references["local_paths"])
    print(
        f"[Stage2] done - 参照画像: {ref_total}件 "
        f"(URL {len(references['urls'])} / ローカル {len(references['local_paths'])}) "
        f"/ 違反チェック項目: {len(spec['violation_features'])}件"
    )

    return {
        "record": record,
        "references": references,
        "spec": spec,
    }


def _build_character_spec(record: dict, form: str) -> dict:
    """形態別の違反検出・修正指示用スペックを構築する。"""
    hints = record.get("ai_hints") or {}
    common = hints.get("common") or {}
    form_data = (hints.get("forms") or {}).get(form) or {}

    if form == "corefolder":
        violation_features = [
            "humanoid arms",
            "human hands or fingers",
            "human legs or feet",
            "standing bipedal human body shape",
            "clothed human torso",
            "human hair visible on spherical body",
        ]
        correction_instruction = (
            "このキャラクターはコアフォルダ形態 (球体型の小動物ロボット) です。\n"
            "- 人型の腕・手・指・脚・足を完全に除去してください\n"
            "- 球体シルエットを維持してください\n"
            "- 直立する人体の胴体・腰・肩ラインを描かないでください"
        )
    else:
        violation_features = [
            "corefolder sphere body instead of humanoid",
            "more than two arms",
            "more than two hands",
            "extra limbs beyond normal human body",
        ]
        correction_instruction = (
            "このキャラクターはヒューマノイド形態 (2本腕・2本脚の人型) です。\n"
            "- 球体コアフォルダ体型を人型に修正してください\n"
            "- 腕は2本、手は2つにしてください\n"
            "- 余分な腕・手を除去してください"
        )

    return {
        "identity_tags": common.get("identity_tags") or [],
        "immutable_traits": _filter_immutable_traits_by_form(
            common.get("immutable_traits") or [], form
        ),
        "form_tags": form_data.get("form_tags") or [],
        "negative_keywords": form_data.get("negative_keywords") or [],
        "violation_features": violation_features,
        "correction_instruction": correction_instruction,
        "form": form,
        "char_name": (
            record["data"].get("Name_JP") or record["data"].get("Name") or (
                f"#{record['data']['Num']:03d}"
                if isinstance(record["data"]["Num"], int)
                else f"#{record['data']['Num']}"
            )
        ),
        "char_num": record["data"]["Num"],
    }


def _save_db_summary(
    stage_dir: Path, record: dict, form: str, references: dict, spec: dict
) -> None:
    summary = {
        "num": record["data"]["Num"],
        "name": record["data"].get("Name_JP") or record["data"].get("Name") or "",
        "form": form,
        "reference_url_count": len(references["urls"]),
        "reference_local_count": len(references["local_paths"]),
        "reference_urls": references["urls"],
        "reference_local_paths": references["local_paths"],
        "character_spec": spec,
    }
    (stage_dir / "db_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
