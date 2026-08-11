"""
tools/verify_appearance_detail.py — AppearanceDetail の実画像照合レビュー
Copyright © RadianN_kswg — CC BY-NC 4.0

創作 DB (`_creations-ai/creations-db`) の `AppearanceDetail` 各エントリを、
同じ DB に登録された**公式イラスト**と OpenAI Vision で 1 行ずつ突き合わせ、
match / mismatch / unclear を判定してレビュー Markdown を生成する。

`--submit` を付けると `gh` CLI で 100BeautiesLab_CreationsDB へ Issue として送る
(既定は生成のみ。`_creations-ai/creations-db/` は read-only 扱いのため直接編集はしない)。

    python -m src.tools.verify_appearance_detail --num 57 --form corefolder
    python -m src.tools.verify_appearance_detail --num 57 --form both --submit
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

from src.utils.dataset import (  # noqa: E402
    apply_generation_gate,
    collect_reference_images,
    find_character,
)
from src.utils.image_io import detect_image_format  # noqa: E402

load_dotenv()

DEFAULT_REPO = "radiann-kswg/100BeautiesLab_CreationsDB"
DEFAULT_DB_BASE = str(_PROJECT_ROOT / "_creations-ai" / "creations-db")
_FORMS = ("corefolder", "humanoid")
_VERDICTS = ("match", "mismatch", "unclear")


# ──────────────────────────────────────────
# 照合に使う公式画像の選定
# ──────────────────────────────────────────

def palette_source_image_keys(work_key: str, creations_db_base: str = DEFAULT_DB_BASE) -> list[str]:
    """作品 typedef の `Images` 子要素のうち `$palette.source` 宣言を持つものの images キーを返す。

    配色抽出の入力に選ばれている画像は、キャラの色と造形が正確に描かれた資料
    (設定原画・設定資料・コアフォルダ画像)。AppearanceDetail の照合にも同じものを使う。
    フィールド名をこちら側へ書かないための入口 (creations-db の `listImageFields()` と同じ考え方)。
    """
    typedef_path = (
        Path(creations_db_base) / "data" / str(work_key).lstrip("#") / "DataBases" / "db_type.json"
    )
    if not typedef_path.exists():
        return []
    try:
        typedef = json.loads(typedef_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    images_def = next(
        (d for d in typedef.get("$DefType") or [] if isinstance(d, dict) and d.get("hashTag") == "Images"),
        None,
    )
    keys: list[str] = []
    for child in (images_def or {}).get("$type") or []:
        if not isinstance(child, dict) or not (child.get("$palette") or {}).get("source"):
            continue
        matched = re.match(r"^(.+)_PNG(?:Name|Path)$", str(child.get("hashTag") or ""))
        if not matched:
            continue
        # ai-dataset 側の images キーは snake_case (`conceptAlt_PNGName` → `concept_alt`)。
        key = re.sub(r"(?<!^)(?=[A-Z])", "_", matched.group(1)).lower()
        if key not in keys:
            keys.append(key)
    return keys


def excluded_for_form(path_text: str, form: str) -> bool:
    """他形態専用と判る画像だけを照合対象から外す。

    生成側の `_is_path_compatible_with_form()` は形態フォルダ以外 (catalog 等) を "other" として
    まとめて落とすが、`$palette.source` 宣言のある画像は形態に依らない設定資料なので残す。
    """
    lower = path_text.replace("\\", "/").lower()
    other = "humanoid" if form == "corefolder" else "corefolder"
    return f"/{other}" in lower


def collect_palette_source_images(
    record: dict, form: str, creations_db_base: str = DEFAULT_DB_BASE
) -> list[Path]:
    """`$palette.source` 宣言のある画像のうち、指定 form の照合に使えるものを返す。"""
    keys = palette_source_image_keys(record.get("work_key") or "#Works_NumberTales", creations_db_base)
    images = record.get("images") or {}
    paths: list[Path] = []
    for key in keys:
        for rel in images.get(key) or []:
            if not isinstance(rel, str) or not rel:
                continue
            path = Path(creations_db_base) / rel
            if path.exists() and not excluded_for_form(rel, form) and path not in paths:
                paths.append(path)
    # 形態名を含む画像を先頭へ (安定ソートなので typedef の宣言順は保たれる)。
    paths.sort(key=lambda p: 0 if f"/{form}" in str(p).replace("\\", "/").lower() else 1)
    return paths


# ──────────────────────────────────────────
# AppearanceDetail → 検査用テキスト
# ──────────────────────────────────────────

def _plain(tag: object) -> str:
    """列挙タグを読める形へ。`#DesignAttr_Position` → `Position`、`#Lat_Right` → `Right`。"""
    text = str(tag or "").lstrip("#")
    return text.split("_", 1)[1] if "_" in text else text


def _attr_text(attr: dict) -> str:
    """Attrs の 1 要素を `Label=value` へ。value_EN → value_JP → vdict_* の順で拾う。"""
    label = _plain(attr.get("AttrLabel"))
    value = attr.get("value_EN") or attr.get("value_JP")
    if not value:
        value = ", ".join(
            _plain(v) for k, v in attr.items() if k.startswith("vdict_") and v
        )
    return f"{label}={value}" if value else label


def entries_for_form(record: dict, form: str) -> list[dict]:
    """AppearanceDetail から指定 form のエントリを返す (Formation が form または null)。"""
    db_record = record.get("db_record") or {}
    data = record.get("data") or {}
    entries = db_record.get("AppearanceDetail") or data.get("AppearanceDetail")
    if not isinstance(entries, list):
        return []
    return [
        e for e in entries
        if isinstance(e, dict) and e.get("Formation") in (form, None)
    ]


def format_entry(index: int, entry: dict) -> str:
    """エントリ 1 件を検査用の 1 行へ整形する。"""
    parts = [_plain(b) for b in (entry.get("BodyPart") or [])] or ["-"]
    lat = _plain(entry.get("Laterality"))
    body = "/".join(parts) + (f"({lat})" if lat else "")
    attrs = " / ".join(
        _attr_text(a) for a in (entry.get("Attrs") or []) if isinstance(a, dict)
    )
    note = entry.get("Note_EN") or entry.get("Note_JP") or ""
    line = f"{index}. [{body}] {_plain(entry.get('DesignElement'))}: {attrs}"
    return line + (f"  (note: {note})" if note else "")


# ──────────────────────────────────────────
# OpenAI Vision による照合
# ──────────────────────────────────────────

def _encode_image(path: Path) -> tuple[str, str]:
    """画像を (mime, base64) へ。MIME は拡張子ではなく実体マジックから決める。"""
    raw = path.read_bytes()
    fmt = detect_image_format(raw[:16])
    return (fmt[1] if fmt else "image/png"), base64.b64encode(raw).decode("utf-8")


def analyze(
    entry_lines: list[str],
    image_paths: list[Path],
    char_name: str,
    form: str,
    model: str,
) -> list[dict]:
    """公式画像と仕様行を突き合わせ、`[{index, verdict, note}, ...]` を返す。"""
    from openai import OpenAI

    system = (
        f"あなたはナンバーテールズ「{char_name}」の {form} 形態の公式イラストを検査する校正 AI です。\n"
        "添付画像は creations-db 登録の公式イラスト (原典) です。\n"
        "提示する仕様行が画像の見た目と一致しているか 1 行ずつ判定し、**JSON のみ**返してください。\n"
        '{"results": [{"index": 1, "verdict": "match", "note": "根拠を日本語で1文"}]}\n'
        "- match:    画像から仕様どおりだと確認できる\n"
        "- mismatch: 画像が仕様と明らかに異なる (位置・色・数・形状のいずれか)\n"
        "- unclear:  画角・遮蔽・解像度・そもそも写っていない等で確認できない\n"
        "推測で match / mismatch にしないこと。判断材料がなければ必ず unclear にしてください。\n"
        "陰影・ハイライト・照明による濃淡差は mismatch ではありません。\n"
        "全ての index を漏れなく返してください。"
    )
    user = "以下は DB に登録された仕様です。1 行ずつ判定してください。\n\n" + "\n".join(entry_lines)

    content: list[dict] = [{"type": "text", "text": user}]
    for path in image_paths:
        mime, b64 = _encode_image(path)
        content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": content},
        ],
        max_tokens=2000,
        response_format={"type": "json_object"},
    )
    raw = json.loads((response.choices[0].message.content or "{}").strip())
    return normalize_results(raw.get("results"), len(entry_lines))


def normalize_results(raw_results: object, count: int) -> list[dict]:
    """モデル出力を index 1..count の判定リストへ正規化する。

    範囲外・重複・不明な verdict は捨て、返ってこなかった行は unclear として残す
    (黙って件数が減ると「照合済み」に見えてしまうため)。
    """
    results: list[dict] = []
    seen: set[int] = set()
    for item in raw_results if isinstance(raw_results, list) else []:
        if not isinstance(item, dict):
            continue
        try:
            index = int(item.get("index"))
        except (TypeError, ValueError):
            continue
        if not (1 <= index <= count) or index in seen:
            continue
        seen.add(index)
        verdict = str(item.get("verdict", "")).lower()
        results.append({
            "index": index,
            "verdict": verdict if verdict in _VERDICTS else "unclear",
            "note": str(item.get("note") or "").strip(),
        })
    for index in range(1, count + 1):
        if index not in seen:
            results.append({"index": index, "verdict": "unclear", "note": "モデルが判定を返しませんでした"})
    return sorted(results, key=lambda r: r["index"])


# ──────────────────────────────────────────
# レビュー Markdown
# ──────────────────────────────────────────

def summarize(results: list[dict]) -> dict[str, int]:
    return {v: sum(1 for r in results if r["verdict"] == v) for v in _VERDICTS}


def build_review_md(
    char_label: str,
    form: str,
    entry_lines: list[str],
    results: list[dict],
    image_paths: list[Path],
    model: str,
    command: str,
    source_label: str,
) -> str:
    counts = summarize(results)
    lines = [
        f"# AppearanceDetail 照合レビュー — {char_label} / {form}",
        "",
        f"- 判定日: {datetime.now():%Y-%m-%d}",
        f"- 解析モデル: `{model}` (画像解析のみ / 生成は行っていません)",
        "- 参照した公式画像: " + ", ".join(f"`{p.name}`" for p in image_paths),
        f"- 画像の選定: {source_label}",
        f"- 結果: match {counts['match']} / **mismatch {counts['mismatch']}** / unclear {counts['unclear']}"
        f" (全 {len(entry_lines)} 件)",
        "",
    ]

    def _cell(text: str) -> str:
        """表崩れ防止。セル内の `|` と改行をエスケープする。"""
        return text.replace("|", "\\|").replace("\n", " ")

    mismatches = [r for r in results if r["verdict"] == "mismatch"]
    if mismatches:
        lines += ["## 要確認 (mismatch)", "", "| # | 仕様 (DB) | 指摘 |", "|---|---|---|"]
        for r in mismatches:
            spec = _cell(entry_lines[r["index"] - 1].split(". ", 1)[-1])
            lines.append(f"| {r['index']} | {spec} | {_cell(r['note'])} |")
        lines.append("")
    else:
        lines += ["## 要確認 (mismatch)", "", "なし。画像から確認できた範囲では仕様と矛盾しませんでした。", ""]

    lines += ["## 全判定", "", "| # | 判定 | 仕様 (DB) | 所見 |", "|---|---|---|---|"]
    for r in results:
        spec = _cell(entry_lines[r["index"] - 1].split(". ", 1)[-1])
        lines.append(f"| {r['index']} | {r['verdict']} | {spec} | {_cell(r['note'])} |")

    lines += [
        "",
        "---",
        "",
        "*本レビューは AI による画像解析の推定であり、`unclear` は「DB が誤り」ではなく"
        "「参照画像からは確認できない」の意味です。最終判断は原典設定を優先してください。*",
        "",
        f"自動生成: `{command}` (100BeautiesLab_GeneratorsAI)",
        "",
    ]
    return "\n".join(lines)


def submit_issue(repo: str, title: str, body_path: Path) -> str:
    proc = subprocess.run(
        ["gh", "issue", "create", "-R", repo, "--title", title, "--body-file", str(body_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if proc.returncode != 0:
        raise SystemExit(f"[ERROR] gh issue create 失敗: {(proc.stderr or '').strip()}")
    return (proc.stdout or "").strip()


# ──────────────────────────────────────────
# CLI
# ──────────────────────────────────────────

def _num_slug(num: object) -> str:
    text = str(num)
    return f"{int(text):03d}" if text.isdigit() else text.replace("/", "-")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="AppearanceDetail を公式画像と照合し、レビュー Markdown を生成する"
    )
    ap.add_argument("--num", required=True, help="キャラクター番号 (例: 57, 2-alt)")
    ap.add_argument("--form", default="corefolder", choices=[*_FORMS, "both"])
    ap.add_argument("--work-key", default="#Works_NumberTales")
    # 2 枚だと humanoid でバストアップ + 尾構造図に偏り、全身の設定画が入らず unclear が増える。
    ap.add_argument("--max-images", type=int, default=3, help="Vision へ渡す公式画像の枚数")
    ap.add_argument("--repo", default=DEFAULT_REPO, help="レビュー送付先リポジトリ")
    ap.add_argument("--submit", action="store_true", help="生成したレビューを Issue として送る (既定は生成のみ)")
    ap.add_argument("--out-dir", default=str(_PROJECT_ROOT / "_ideas" / "db-reviews"))
    args = ap.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("[ERROR] OPENAI_API_KEY が未設定です (.env を確認してください)")

    record = find_character(args.num, work_key=args.work_key)
    if not record:
        raise SystemExit(f"[ERROR] キャラクターが見つかりません: num={args.num}")

    # 公式画像を LLM へ送るため、生成入口と同じ fail-closed ゲートを通す。
    proceed, _gate = apply_generation_gate(record, usage="image", num=args.num, printer=print)
    if not proceed:
        raise SystemExit(1)

    data = record.get("data") or {}
    # Name_JP は "57(イズナ)" のように番号込みなので、Num を足すと二重になる。
    char_label = str(data.get("Name_JP") or data.get("Name_EN") or data.get("Num") or args.num)
    model = os.environ.get("GPT_MODEL", "gpt-4o")
    forms = _FORMS if args.form == "both" else (args.form,)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for form in forms:
        entries = entries_for_form(record, form)
        if not entries:
            print(f"[SKIP] {form}: 対象の AppearanceDetail エントリがありません")
            continue

        # 配色抽出対象 ($palette.source) の画像を優先する。宣言の無い作品は従来の参照画像へ落とす。
        image_paths = collect_palette_source_images(record, form)
        source_label = "typedef `$palette.source` 宣言画像"
        if not image_paths:
            image_paths = [
                p for p in (
                    Path(x) for x in collect_reference_images(
                        record, form, creations_db_base=DEFAULT_DB_BASE
                    )["local_paths"]
                ) if p.exists()
            ]
            source_label = "参照画像フォールバック (`$palette.source` 宣言なし)"
        image_paths = image_paths[: args.max_images]
        if not image_paths:
            print(f"[SKIP] {form}: 照合できるローカル公式画像がありません")
            continue

        entry_lines = [format_entry(i, e) for i, e in enumerate(entries, 1)]
        print(f"[{form}] 照合に使う公式画像 ({source_label}): {', '.join(p.name for p in image_paths)}")
        print(f"[{form}] {len(entry_lines)} 件を {len(image_paths)} 枚の公式画像と照合中 ({model})...")
        results = analyze(entry_lines, image_paths, char_label, form, model)
        counts = summarize(results)
        print(f"[{form}] match {counts['match']} / mismatch {counts['mismatch']} / unclear {counts['unclear']}")

        command = f"python -m src.tools.verify_appearance_detail --num {args.num} --form {form}"
        body = build_review_md(
            char_label, form, entry_lines, results, image_paths, model, command, source_label
        )
        out_path = out_dir / f"{datetime.now():%Y%m%d}_appearance_num{_num_slug(data.get('Num'))}_{form}.md"
        out_path.write_text(body, encoding="utf-8")
        print(f"[{form}] レビュー生成: {out_path}")

        if args.submit:
            title = (
                f"[AppearanceDetail 照合] {char_label} / {form}"
                f" — mismatch {counts['mismatch']} / unclear {counts['unclear']}"
            )
            print(f"[{form}] Issue 送信: {submit_issue(args.repo, title, out_path)}")


if __name__ == "__main__":
    main()
