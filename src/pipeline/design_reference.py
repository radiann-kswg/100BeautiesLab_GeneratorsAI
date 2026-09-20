"""Stage 2 の画像観察。AIHints を正典として Stage 3/4 へ渡す。"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

from src.utils.image_io import load_reference_bytes
from src.utils.run_log import initialize_run_logs, write_run_meta
from src.utils.dataset import _creations_db_repo_root, _image_category, extract_char_name


class ReferenceConfirmationRequired(RuntimeError):
    """非対話実行では警告を保存して止め、明示回答を待つ。"""


class ReferenceCancelled(RuntimeError):
    """利用者が画像観察なしの続行を拒否した。"""


def confirm_in_terminal(warning: dict) -> bool:
    print(json.dumps(warning, ensure_ascii=False, indent=2))
    try:
        return input("AIHints と既存参照画像だけで続行しますか？ [y/N]: ").strip().lower() == "y"
    except EOFError as exc:
        raise ReferenceConfirmationRequired(
            "画像観察に失敗し、入力端末がありません。分割CLIなら同じ run-dir の stage2 "
            "--reference-decision で回答できます。通しCLIは対話端末で起動してください（再起動は新規実行）。"
        ) from exc


def _observe(prompt: str, references: dict) -> dict:
    from openai import OpenAI

    if not os.environ.get("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY が未設定のため画像観察を実行できません")

    content: list[dict] = [{"type": "text", "text": prompt}]
    sources: list[str] = []
    for path in references.get("local_paths", []):
        if not Path(path).is_file():
            continue
        loaded = load_reference_bytes(path)
        if loaded:
            raw, mime = loaded
            content.append({"type": "image_url", "image_url": {
                "url": f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"}})
            sources.append(str(path))
        if len(sources) == 3:
            break
    # ローカルが無い環境でも DB が解決した公式 URL のみを利用する。
    if not sources:
        for url in references.get("urls", [])[:3]:
            content.append({"type": "image_url", "image_url": {"url": url}})
            sources.append(url)
    if not sources:
        raise ValueError("利用できる公式設定画像がありません")
    response = OpenAI(timeout=90, max_retries=0).chat.completions.create(
        model=os.environ.get("GPT_MODEL", "gpt-4o"),
        messages=[{"role": "user", "content": content}],
        response_format={"type": "json_object"},
    )
    result = json.loads(response.choices[0].message.content or "null")
    if not isinstance(result, dict):
        raise ValueError("画像観察の応答が JSON オブジェクトではありません")
    for key in ("observations", "unknowns", "conflicts"):
        if not isinstance(result.get(key), list) or not all(isinstance(x, str) for x in result[key]):
            raise ValueError(f"画像観察の {key} が文字列配列ではありません")
    if not result["observations"]:
        raise ValueError("画像から特徴を読み取れませんでした")
    return {key: result[key] for key in ("observations", "unknowns", "conflicts")} | {"sources": sources}


def _official_settings(references: dict) -> dict:
    """既存 resolver の本人・形態照合後、DB 内の設定画だけを観察対象にする。"""
    categories = {"concept", "concept_alt", "design", "design_alt", "catalog", "corefolder", "humanoid", "tails_unit"}
    root = _creations_db_repo_root().resolve()
    local = [p for p in references.get("local_paths", [])
             if Path(p).resolve().is_relative_to(root) and _image_category(p) in categories]
    urls = [u for u in references.get("urls", [])
            if urlparse(u).scheme == "https" and urlparse(u).hostname == "database.numbertales-radiann.net"
            and urlparse(u).path.startswith("/data/") and _image_category(u) in categories]
    return {"local_paths": local, "urls": urls}


def collect_design_reference(
    record: dict, form: str, references: dict, stage_dir: Path,
    confirm: Callable[[dict], bool | None] | None = None,
) -> dict:
    """同一実行の保存済み結果を再利用。失敗時は明示承認まで呼出元へ戻らない。"""
    hints = record.get("ai_hints") or {}
    canonical = {"common": hints.get("common") or {},
                 "form": (hints.get("forms") or {}).get(form) or {}}
    log_dir = stage_dir / "design_reference"
    meta_path = log_dir / "run_meta.json"
    saved = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    if saved:
        if saved.get("ai_hints") != canonical or saved.get("references") != references:
            raise ValueError("同一実行の AIHints/参照画像が変わっています。新規実行してください。")
        if saved.get("status") in ("ok", "fallback_approved"):
            return saved["design_reference"]
        if saved.get("status") == "cancelled":
            raise ReferenceCancelled("この実行は中止済みです。新規実行してください。")
    prompt = (
        f"公式設定画像の #{record['data']['Num']} {extract_char_name(record)} の {form} 形態だけを観察してください。"
        "他キャラクターの特徴は含めないでください。以下の AIHints 文面が正典です。\n"
        "画像観察で AIHints を上書きしないでください。他形態の特徴を混ぜないでください。\n"
        "耳・尻尾の本数と束構成・シルエット・配色・番号・非対称要素を観察してください。\n"
        "左右はキャラクター自身の左右と画像上の左右を区別。隠れた部位は推測せず不明にしてください。\n"
        "JSON の observations / unknowns / conflicts に文字列配列で返してください。"
        "AIHints と矛盾する観察は conflicts のみに入れてください。\n[AIHints 原文]\n"
        + json.dumps(canonical, ensure_ascii=False)
    )
    design = {"ai_hints": canonical, "observations": [], "unknowns": [], "conflicts": [], "sources": []}
    design["num"] = record["data"]["Num"]
    design["form"] = form
    if not saved:
        initialize_run_logs(log_dir, provider="openai", num=record["data"]["Num"],
                            form=form, work_key=record.get("work_key", "#Works_NumberTales"),
                            model=os.environ.get("GPT_MODEL", "gpt-4o"), prompt_text=prompt,
                            meta={"ai_hints": canonical, "references": references})
        try:
            if not hints:
                raise ValueError("CreationsAI の AIHints がありません")
            design.update(_observe(prompt, _official_settings(references)))
        except Exception as exc:
            # SDK エラー本文には URL 等が入るため種類だけ公開する。
            reason = str(exc) if isinstance(exc, ValueError) else {
                "AuthenticationError": "OpenAI API の認証に失敗しました",
                "RateLimitError": "OpenAI API の利用上限またはレート制限に達しました",
                "APITimeoutError": "公式画像の観察 API が時間内に応答しませんでした",
                "APIConnectionError": "OpenAI API に接続できませんでした",
                "BadRequestError": "OpenAI API が参照画像または観察リクエストを受け付けませんでした",
                "ModuleNotFoundError": "画像観察に必要なライブラリがありません",
            }.get(type(exc).__name__, f"画像観察に失敗しました ({type(exc).__name__})")
            warning = {"status": "awaiting_confirmation", "num": record["data"]["Num"],
                       "form": form, "reason": reason, "log_dir": str(log_dir),
                       "question": "画像観察に失敗しました。AIHints と既存参照画像だけで続行しますか？"}
            write_run_meta(log_dir, {"status": "awaiting_confirmation", "warning": warning})
        else:
            write_run_meta(log_dir, {"status": "ok", "design_reference": design})
            return design
    else:
        warning = saved.get("warning") or {
            "status": "awaiting_confirmation", "reason": "前回の画像観察が未完了です",
            "num": record["data"]["Num"], "form": form, "log_dir": str(log_dir)}
    approved = (confirm or confirm_in_terminal)(warning)
    if approved is not True:
        write_run_meta(log_dir, {"status": "cancelled",
                                "user_decision": "cancel" if approved is False else "not_received"})
        raise ReferenceCancelled("画像観察なしの続行が承認されなかったため、ラフ生成前に中止しました。")
    design["fallback"] = True
    write_run_meta(log_dir, {"status": "fallback_approved", "user_decision": "continue",
                            "design_reference": design})
    return design


def design_reference_block(design: dict) -> str:
    return (
        "[キャラクターデザイン遵守]\n"
        "AIHints は正典。対象形態に適用される原文を守ること。画像観察は補助情報であり、"
        "AIHints と衝突したら採用しない。不明点・矛盾を確定特徴として描かない。\n"
        "公式画像は個体デザイン、構図ガイド・過去の生成画像は構図だけの参考。"
        "シーンや衣装変更でも不変特徴を変えない。\n"
        + json.dumps(design, ensure_ascii=False) + "\n\n"
    )


def add_design_reference(prompts: dict, spec: dict) -> dict:
    block = design_reference_block(spec["design_reference"])
    return {key: block + value if key in ("base_gemini", "gemini", "openai") and isinstance(value, str)
            and not value.startswith(block) else value for key, value in prompts.items()}
