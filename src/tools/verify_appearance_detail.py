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
import tempfile
from concurrent.futures import ThreadPoolExecutor
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
    load_manifest,
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

def palette_source_image_keys(
    work_key: str, creations_db_base: str = DEFAULT_DB_BASE, source: str | None = None
) -> list[str]:
    """作品 typedef の `Images` 子要素のうち `$palette.source` 宣言を持つものの images キーを返す。

    ``source`` を指定するとその宣言値のものだけ（``"artwork"`` = 透過キャラ単体イラスト等）。

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
        if not isinstance(child, dict):
            continue
        declared = (child.get("$palette") or {}).get("source")
        if not declared or (source is not None and declared != source):
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
    record: dict,
    form: str | None,
    creations_db_base: str = DEFAULT_DB_BASE,
    source: str | None = None,
) -> list[Path]:
    """`$palette.source` 宣言のある画像のうち、指定 form の照合に使えるものを返す。

    ``form=None`` は形態で絞らない（両形態を 1 度に見たい一括検査用）。
    ``source`` は `$palette.source` の宣言値で絞る（``"artwork"`` = 実測色の抽出元）。
    """
    keys = palette_source_image_keys(
        record.get("work_key") or "#Works_NumberTales", creations_db_base, source
    )
    images = record.get("images") or {}
    paths: list[Path] = []
    for key in keys:
        for rel in images.get(key) or []:
            if not isinstance(rel, str) or not rel:
                continue
            path = Path(creations_db_base) / rel
            if not path.exists() or path in paths:
                continue
            if form is not None and excluded_for_form(rel, form):
                continue
            paths.append(path)
    if form is not None:
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


# ──────────────────────────────────────────
# 配色検知ツール向けの充足性検査 (--check coverage)
# ──────────────────────────────────────────

# 上流 `tools/extract-palette.mjs` をそのまま呼ぶ。色語表 (COLOR_WORD_RANGES) と
# collectColorHints() は配色検知ツールの判定の正典で、こちらへ再実装すると必ず食い違う。
_NODE_EVIDENCE_SCRIPT = """
import {
    collectColorHints, colorWordMatchesHex, readCommonColors,
    decodePng, extractSolidColors, isTransparentArtwork, colorDistance,
} from %(module)s;
import fs from 'node:fs';
// ponytail: 色語 key の一覧だけこちらに持つ。判定自体は上流の colorWordMatchesHex に委ねるので、
// 上流が語を増やしたらここへ追記が要る（提案が出ないだけで、誤った提案は出ない）。
const COLOR_WORD_KEYS = ['red', 'red orange', 'orange', 'yellow', 'green', 'cyan', 'blue',
    'purple', 'pink', 'brown', 'white', 'black', 'gray'];
const payload = JSON.parse(fs.readFileSync(process.argv[1], 'utf8'));
const records = payload.map((p) => p.record);
const commonColors = readCommonColors(process.argv[2]) ?? [];

/**
 * 透過イラストから実測した色のうち、既存 ColorPalette のどれとも一致しないものを返す。
 * 抽出条件は上流 `patch-colorpalette.mjs --from-artwork` と揃える（共通造形色を除外）。
 */
function detectMissingColors(rec, artworkPaths) {
    const images = [];
    for (const p of artworkPaths ?? []) {
        try {
            const img = decodePng(fs.readFileSync(p));
            if (isTransparentArtwork(img)) images.push(img);
        } catch { /* 読めない画像は黙って飛ばす */ }
    }
    if (!images.length) return [];
    const existing = (rec.ColorPalette ?? []).map((c) => c.Hex).filter((h) => typeof h === 'string');
    // ponytail: 「既存と同じ色」の許容差は上流の mergeTol(10) に合わせた固定値。
    // 取りこぼし/過剰報告が出るようならここを調整する。
    return extractSolidColors(images, { exclude: commonColors })
        .filter((d) => !existing.some((h) => colorDistance(h, d.hex) <= 10));
}
const attrText = (a) => {
    const vdict = Object.entries(a).filter(([k]) => k.startsWith('vdict_')).map(([, v]) => v).join(', ');
    return `${a.AttrLabel ?? '?'}: ${a.value_EN ?? a.value_JP ?? vdict ?? ''}`;
};
const evidence = records.map((rec, ri) => {
    const details = Array.isArray(rec.AppearanceDetail) ? rec.AppearanceDetail : [];
    const entries = details.map((e, i) => ({
        index: i + 1,
        formation: e.Formation ?? null,
        bodyPart: Array.isArray(e.BodyPart) ? e.BodyPart : [],
        element: e.DesignElement ?? null,
        text: (Array.isArray(e.Attrs) ? e.Attrs : []).map(attrText).join(' / '),
        hints: collectColorHints({ AppearanceDetail: [e] }),
    }));
    const allHints = collectColorHints(rec);
    const palette = (Array.isArray(rec.ColorPalette) ? rec.ColorPalette : []).map((c) => ({
        hex: c.Hex,
        role: c.Role ?? null,
        appliesTo: c.AppliesTo ?? null,
        formation: c.Formation ?? null,
        hints: typeof c.Hex === 'string' ? allHints.filter((h) => colorWordMatchesHex(h.word, c.Hex)) : [],
        // その HEX に該当する色語 (記述へ書けば配色ツールが拾える語)。
        colorWords: typeof c.Hex === 'string'
            ? COLOR_WORD_KEYS.filter((w) => colorWordMatchesHex(w, c.Hex))
            : [],
    }));
    return { entries, palette, missingColors: detectMissingColors(rec, payload[ri].artwork) };
});
// 共通造形色 (肌色・毛色など) は設計上 ColorPalette から除外されるため、
// 「画像にあるのに ColorPalette に無い」の指摘対象から外す必要がある。
const commonWords = [...new Set(
    commonColors.flatMap((hex) => COLOR_WORD_KEYS.filter((w) => colorWordMatchesHex(w, hex)))
)];
process.stdout.write(JSON.stringify({ evidence, commonWords }));
"""


def collect_color_hint_evidence(
    records: list[dict],
    creations_db_base: str = DEFAULT_DB_BASE,
    work_key: str = "#Works_NumberTales",
) -> tuple[list[dict], list[str]]:
    """配色検知ツールが実際に拾える色語ヒントを、上流ツールを呼んで取得する。

    node の起動コストがあるため、複数レコードは 1 プロセスでまとめて処理する。
    返り値は ``(レコードごとの evidence, 共通造形色に該当する色語)``。
    """
    module = Path(creations_db_base) / "tools" / "extract-palette.mjs"
    if not module.exists():
        raise SystemExit(f"[ERROR] 配色ツールが見つかりません: {module}")
    work_dir = Path(creations_db_base) / "data" / str(work_key).lstrip("#")

    payload = [
        {
            "record": r.get("db_record") or r.get("data") or {},
            # 実測色の抽出元は `$palette.source: artwork` の透過イラストのみ。
            "artwork": [
                str(p) for p in collect_palette_source_images(
                    r, None, creations_db_base, source="artwork"
                )
            ],
        }
        for r in records
    ]
    with tempfile.TemporaryDirectory() as tmp:
        rec_path = Path(tmp) / "records.json"
        rec_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        proc = subprocess.run(
            [
                "node", "--input-type=module",
                "-e", _NODE_EVIDENCE_SCRIPT % {"module": json.dumps(module.as_uri())},
                str(rec_path), str(work_dir),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    if proc.returncode != 0:
        raise SystemExit(f"[ERROR] 色語ヒントの取得に失敗 (node): {(proc.stderr or '').strip()}")
    result = json.loads(proc.stdout)
    return result["evidence"], result.get("commonWords") or []


def audit_coverage(evidence: dict, form: str | None) -> dict:
    """配色検知ツールが `AppliesTo` を埋められない箇所を洗い出す。

    ``form=None`` は形態で絞らない (一括検査用。欠落は形態に関係なく欠落のため)。
    """
    def _in_form(item: dict) -> bool:
        return form is None or item.get("formation") in (form, None)

    entries = [e for e in evidence.get("entries") or [] if _in_form(e)]
    palette = [c for c in evidence.get("palette") or [] if _in_form(c)]
    return {
        "entries": entries,
        "palette": palette,
        # 透過イラストから実測したが ColorPalette に無い色 (形態別ではないので素通し)。
        "missing_colors": evidence.get("missingColors") or [],
        # 色語はあるのに部位が無い → AppliesTo へ転記できない。最優先。
        "missing_body_part": [e for e in entries if e["hints"] and not e["bodyPart"]],
        # 色語を 1 つも生まないエントリ → 色語表に無い語 (blonde / amber 等) の可能性。
        "no_color_word": [e for e in entries if not e["hints"]],
        # 根拠となる色語が無い HEX → その色がどの部位か決められない。
        "unbacked_hex": [c for c in palette if not c["hints"]],
    }


def load_design_enums(creations_db_base: str = DEFAULT_DB_BASE) -> dict[str, dict[str, str]]:
    """`$EnumDef_DesignBodyPart` / `$EnumDef_DesignElement` をコード → 日本語ラベルで返す。"""
    meta_path = Path(creations_db_base) / "data" / "db_meta.json"
    if not meta_path.exists():
        return {"body_part": {}, "element": {}}
    vars_def = (json.loads(meta_path.read_text(encoding="utf-8")).get("General") or {}).get("$VarsDef") or {}

    def _labels(key: str, label_key: str) -> dict[str, str]:
        return {
            code: str(entry.get(label_key) or code)
            for code, entry in (vars_def.get(key) or {}).items()
            if isinstance(entry, dict)
        }

    return {
        "body_part": _labels("$EnumDef_DesignBodyPart", "BodyPart_JP"),
        "element": _labels("$EnumDef_DesignElement", "DesignElement_JP"),
    }


def suggest_body_parts(
    audit: dict,
    enums: dict,
    image_paths: list[Path],
    char_label: str,
    form: str,
    model: str,
) -> dict[str, dict]:
    """不足箇所に当てる BodyPart コードを公式画像から提案させる (半自動の下書き)。"""
    items: list[str] = []
    for entry in audit["missing_body_part"]:
        items.append(f'A-{entry["index"]}. 記述: "{entry["text"]}" (DesignElement: {entry["element"]})')
    for color in audit["unbacked_hex"]:
        items.append(f'H-{color["hex"]}. 色 {color["hex"]} が塗られている部位')
    if not items or not image_paths:
        return {}

    from openai import OpenAI

    body_part_list = "\n".join(f"- {code} ({label})" for code, label in enums["body_part"].items())
    system = (
        f"あなたは創作 DB の記述を補う校正 AI です。対象は「{char_label}」の {form} 形態です。\n"
        "添付画像は公式イラスト (原典) です。各項目について、当てはまる BodyPart コードを"
        "**下の一覧から**選び、**JSON のみ**返してください。\n"
        '{"suggestions": [{"id": "A-5", "body_parts": ["#BodyPart_Chest"], "note": "根拠を日本語で1文"}]}\n'
        f"[BodyPart コード一覧]\n{body_part_list}\n"
        "画像から判断できない項目は body_parts を空配列にし、note に理由を書いてください。"
        "一覧に無いコードを作らないでください。"
    )
    content: list[dict] = [{"type": "text", "text": "以下の項目に当てはまる部位を挙げてください。\n\n" + "\n".join(items)}]
    for path in image_paths:
        mime, b64 = _encode_image(path)
        content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": content}],
        max_tokens=1500,
        response_format={"type": "json_object"},
    )
    raw = json.loads((response.choices[0].message.content or "{}").strip())

    valid = set(enums["body_part"])
    out: dict[str, dict] = {}
    for item in raw.get("suggestions") or []:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        # 一覧に無いコードを提案してくることがあるので捨てる (そのまま DB へ貼れる形を保つ)。
        parts = [p for p in (item.get("body_parts") or []) if p in valid]
        out[str(item["id"])] = {"body_parts": parts, "note": str(item.get("note") or "").strip()}
    return out


def build_coverage_md(
    char_label: str,
    form: str,
    audit: dict,
    enums: dict,
    suggestions: dict,
    image_paths: list[Path],
    model: str,
    command: str,
) -> str:
    def _cell(text: str) -> str:
        return str(text).replace("|", "\\|").replace("\n", " ")

    def _parts(codes: list[str]) -> str:
        return ", ".join(f"`{c}` ({enums['body_part'].get(c, '?')})" for c in codes) or "—"

    def _suggestion(key: str) -> str:
        found = suggestions.get(key)
        if not found:
            return "—"
        if not found["body_parts"]:
            return f"(判断できず) {_cell(found['note'])}"
        return f"{_parts(found['body_parts'])} — {_cell(found['note'])}"

    entries, palette = audit["entries"], audit["palette"]
    with_hints = [e for e in entries if e["hints"]]
    lines = [
        f"# AppearanceDetail 充足性レビュー（配色検知ツール向け） — {char_label} / {form}",
        "",
        "配色検知ツール (`tools/patch-colorpalette.mjs`) は `AppearanceDetail` の色語から",
        "`ColorPalette.AppliesTo`（その色がどの部位か）を転記する。したがって **色語を含むエントリに",
        "`BodyPart` が無いと、検出した色を部位へ紐づけられない**。",
        "以下は上流の `collectColorHints()` / `colorWordMatchesHex()` を直接呼んで得た充足状況で、",
        "判定ロジックの再実装はしていない。",
        "",
        f"- 判定日: {datetime.now():%Y-%m-%d}",
        f"- 色語ヒントを持つエントリ: {len(with_hints)} / {len(entries)}",
        f"- **BodyPart 欠落: {len(audit['missing_body_part'])} 件**（AppliesTo へ転記できない）",
        f"- **根拠となる色語が無い ColorPalette: {len(audit['unbacked_hex'])} 色** / 全 {len(palette)} 色",
        f"- 色語ヒント 0 のエントリ: {len(audit['no_color_word'])} 件（色語表に無い語の可能性）",
    ]
    if suggestions:
        lines.append(
            "- 部位候補: 公式画像 " + ", ".join(f"`{p.name}`" for p in image_paths) + f" から `{model}` が提案"
        )
    lines.append("")

    lines += ["## 1. BodyPart 欠落（最優先）", ""]
    if audit["missing_body_part"]:
        lines += ["| # | DesignElement | 記述 | 検出された色語 | 画像からの部位候補 |", "|---|---|---|---|---|"]
        for entry in audit["missing_body_part"]:
            words = ", ".join(sorted({h["word"] for h in entry["hints"]}))
            element = f"`{entry['element']}`" if entry["element"] else "—"
            hint = _suggestion(f"A-{entry['index']}")
            lines.append(
                f"| {entry['index']} | {element} | {_cell(entry['text'])} | {words} | {hint} |"
            )
        lines.append("")
    else:
        lines += ["なし。色語を含むエントリにはすべて `BodyPart` が入っている。", ""]

    lines += ["## 2. 根拠となる色語が無い ColorPalette", ""]
    if audit["unbacked_hex"]:
        lines += ["| HEX | Role | 現在の AppliesTo | 画像からの部位候補 |", "|---|---|---|---|"]
        for color in audit["unbacked_hex"]:
            lines.append(
                f"| `{color['hex']}` | {color['role'] or '—'} | {_parts(color['appliesTo'] or [])} |"
                f" {_suggestion('H-' + str(color['hex']))} |"
            )
        lines.append("")
    else:
        lines += ["なし。すべての色に対応する色語がある。", ""]

    lines += [
        "## 3. 色語ヒント 0 のエントリ（参考）",
        "",
        "配色ツールの色語表に載っている語が記述に含まれていない。形状のみを述べたエントリなら正常。",
        "`blonde` / `amber` のような色を指す語は現在の色語表に無いため、拾われない。",
        "",
    ]
    if audit["no_color_word"]:
        lines += ["| # | BodyPart | DesignElement | 記述 |", "|---|---|---|---|"]
        for entry in audit["no_color_word"]:
            element = f"`{entry['element']}`" if entry["element"] else "—"
            lines.append(
                f"| {entry['index']} | {_parts(entry['bodyPart'])} | {element} | {_cell(entry['text'])} |"
            )
        lines.append("")
    else:
        lines += ["なし。", ""]

    lines += [
        "---",
        "",
        "*部位候補は AI が公式画像から推定した**下書き**です。DB へ反映する前に原典設定で確認してください。*",
        "",
        f"自動生成: `{command}` (100BeautiesLab_GeneratorsAI)",
        "",
    ]
    return "\n".join(lines)


# ──────────────────────────────────────────
# 一括検査 (--all)
# ──────────────────────────────────────────

def extract_unknown_color_words(texts: list[str], model: str, batch_size: int = 60) -> dict[str, list[str]]:
    """色語表に拾われなかった記述から、色を指す語を抽出する (テキストのみ・画像不要)。

    `blonde` / `amber` のように配色ツールの `COLOR_WORD_RANGES` に無い語を洗い出すのが目的。
    記述の語彙はキャラ間で重複が多いため、ユニークな文字列だけを投げる。
    """
    if not texts:
        return {}
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    system = (
        "あなたは創作 DB の外見記述を解析する AI です。\n"
        "各記述について、**色を指している語**だけを抜き出し、**JSON のみ**返してください。\n"
        '{"results": [{"text": "blonde ponytail", "color_words": ["blonde"]}]}\n'
        "- 色を指す語がなければ color_words を空配列にしてください。\n"
        "- 形状・素材・部位の語 (ponytail / fox / armband など) は色ではありません。\n"
        "- 記述は原文のまま text に返してください。\n"
        "- 全ての記述を漏れなく返してください。"
    )

    out: dict[str, list[str]] = {}
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": "\n".join(f"- {t}" for t in batch)},
            ],
            max_tokens=3000,
            response_format={"type": "json_object"},
        )
        raw = json.loads((response.choices[0].message.content or "{}").strip())
        known = set(batch)
        for item in raw.get("results") or []:
            if not isinstance(item, dict):
                continue
            text = str(item.get("text") or "")
            words = [str(w).strip().lower() for w in (item.get("color_words") or []) if str(w).strip()]
            # 原文を書き換えて返してくることがあるので、投げた文字列に一致するものだけ採る。
            if text in known and words:
                out[text] = words
    return out


def build_bulk_coverage_md(
    audits: list[tuple[str, dict]],
    enums: dict,
    unknown_words: dict[str, list[str]],
    work_key: str,
    model: str,
    command: str,
) -> str:
    def _cell(text: str) -> str:
        return str(text).replace("|", "\\|").replace("\n", " ")

    def _parts(codes: list[str]) -> str:
        return ", ".join(f"`{c}` ({enums['body_part'].get(c, '?')})" for c in codes) or "—"

    missing = [(label, e) for label, a in audits for e in a["missing_body_part"]]
    unbacked = [(label, c) for label, a in audits for c in a["unbacked_hex"]]
    chars_missing = len({label for label, _ in missing})
    chars_unbacked = len({label for label, _ in unbacked})

    # 拾われていない色語を出現数の多い順に集計する (色語表へ何を足すべきかの優先順)。
    word_stats: dict[str, dict] = {}
    for label, audit in audits:
        for entry in audit["no_color_word"]:
            for word in unknown_words.get(entry["text"], []):
                stat = word_stats.setdefault(word, {"count": 0, "chars": set(), "examples": []})
                stat["count"] += 1
                stat["chars"].add(label)
                if len(stat["examples"]) < 2 and entry["text"] not in stat["examples"]:
                    stat["examples"].append(entry["text"])

    lines = [
        f"# AppearanceDetail 充足性レビュー（配色検知ツール向け・一括） — {work_key}",
        "",
        "配色検知ツール (`tools/patch-colorpalette.mjs`) は `AppearanceDetail` の色語から",
        "`ColorPalette.AppliesTo` を転記する。**色語が拾えない／`BodyPart` が無い**と、",
        "検出した色を部位へ紐づけられない。以下はその不足の一覧。",
        "",
        "判定は上流 `tools/extract-palette.mjs` の `collectColorHints()` / `colorWordMatchesHex()` を",
        "直接呼んで得ている（判定ロジックの再実装なし）。形態では絞っていない（欠落は形態に依らないため）。",
        "",
        f"- 判定日: {datetime.now():%Y-%m-%d}",
        f"- 対象レコード: {len(audits)} 件",
        f"- **BodyPart 欠落: {len(missing)} 件 / {chars_missing} キャラ**",
        f"- **根拠となる色語が無い ColorPalette: {len(unbacked)} 色 / {chars_unbacked} キャラ**",
        f"- 色語表に無い色語: {len(word_stats)} 種",
        "",
    ]

    lines += [
        "## 1. 色語表に無い色語（配色ツール側で対応すると全キャラに効く）",
        "",
        "記述には色が書かれているのに `COLOR_WORD_RANGES` に該当語が無く、ヒントが生成されないもの。",
        f"色語の抽出には `{model}` を使用（画像は見ていない）。",
        "",
    ]
    def _example(text: str, limit: int = 70) -> str:
        """`#DesignAttr_Overview: blonde ponytail` → `blonde ponytail`（表に収まる長さへ）。"""
        short = " / ".join(part.split(": ", 1)[-1] for part in str(text).split(" / "))
        short = _cell(short)
        return short[:limit] + ("…" if len(short) > limit else "")

    if word_stats:
        lines += ["| 色語 | 出現 | キャラ数 | 記述例 |", "|---|---|---|---|"]
        for word, stat in sorted(word_stats.items(), key=lambda kv: -kv[1]["count"]):
            examples = " / ".join(f"`{_example(x)}`" for x in stat["examples"][:1])
            lines.append(f"| **{_cell(word)}** | {stat['count']} | {len(stat['chars'])} | {examples} |")
        lines.append("")
    else:
        lines += ["なし。", ""]

    lines += [
        "## 2. BodyPart 欠落（DB 側の記述で埋める）",
        "",
        "色語は拾えているのに `BodyPart` が空で、`AppliesTo` へ転記できないエントリ。",
        "",
    ]
    if missing:
        lines += ["| キャラ | # | DesignElement | 記述 | 色語 |", "|---|---|---|---|---|"]
        for label, entry in missing:
            words = ", ".join(sorted({h["word"] for h in entry["hints"]}))
            element = f"`{entry['element']}`" if entry["element"] else "—"
            lines.append(
                f"| {label} | {entry['index']} | {element} | {_example(entry['text'], 90)} | {words} |"
            )
        lines.append("")
    else:
        lines += ["なし。", ""]

    lines += [
        "## 3. 根拠となる色語が無い ColorPalette",
        "",
        "検出済みの色に対応する色語が記述に無く、`AppliesTo` を決められないもの。",
        "1 の色語を追加すると解消するものが含まれる。",
        "",
    ]
    if unbacked:
        lines += ["| キャラ | HEX | Role | 現在の AppliesTo |", "|---|---|---|---|"]
        for label, color in unbacked:
            lines.append(
                f"| {label} | `{color['hex']}` | {color['role'] or '—'} | {_parts(color['appliesTo'] or [])} |"
            )
        lines.append("")
    else:
        lines += ["なし。", ""]

    lines += [
        "---",
        "",
        "*色語の抽出は AI による判定です。DB や色語表へ反映する前に確認してください。*",
        "*個別キャラの部位候補（画像からの提案）は `--num <N> --check coverage` で出せます。*",
        "",
        f"自動生成: `{command}` (100BeautiesLab_GeneratorsAI)",
        "",
    ]
    return "\n".join(lines)


# 色語 key → 日本語。上流 COLOR_WORD_RANGES の jp[0] に合わせる。
# ponytail: 判定は上流が持つのでラベルだけの写し。上流が語を増やしたら追記が要る（欠けても英語だけ出る）。
_COLOR_WORD_JP = {
    "red": "赤", "red orange": "朱", "orange": "橙", "yellow": "黄", "green": "緑",
    "cyan": "水色", "blue": "青", "purple": "紫", "pink": "桃", "brown": "茶",
    "white": "白", "black": "黒", "gray": "灰",
}


def detect_colors_from_images(
    entries: list[dict],
    image_paths: list[Path],
    char_label: str,
    model: str,
) -> dict[int, dict]:
    """色情報が無いエントリについて、**公式画像を正典として**色語を読み取る。

    `ColorPalette` の HEX は配色検知ツールが画像から起こした出力であり、それ自体が
    不完全でありうる（補完したい対象そのもの）。HEX から色語を逆引きすると誤りを
    自己肯定してしまうため、色の根拠は公式画像に置く。
    """
    if not entries or not image_paths:
        return {}
    from openai import OpenAI

    word_list = " / ".join(f"{w} ({jp})" for w, jp in _COLOR_WORD_JP.items())
    system = (
        f"あなたは創作 DB の外見記述を補う校正 AI です。対象は「{char_label}」です。\n"
        "添付画像は公式イラスト (原典) で、これが色の唯一の根拠です。\n"
        "各項目について、画像でその要素が実際に何色に塗られているかを読み取り、"
        "**下の色語一覧から**選んで**JSON のみ**返してください。\n"
        '{"suggestions": [{"index": 1, "color_words": ["yellow"], "note": "根拠を日本語で1文"}]}\n'
        f"[色語一覧]\n{word_list}\n"
        "- 一覧に無い語を作らないでください（一覧は配色検知ツールが認識できる語の全てです）。\n"
        "- 中間色は近い語を複数挙げて構いません（例: 黄緑なら yellow と green）。\n"
        "- 画像で該当箇所が確認できない項目は color_words を空配列にし、note に理由を書いてください。\n"
        "- 推測で色を決めないでください。"
    )
    items = "\n".join(f"{e['index']}. {e['text']}" for e in entries)
    content: list[dict] = [
        {"type": "text", "text": "以下は色情報が入っていない記述です。画像から実際の色を読み取ってください。\n\n" + items}
    ]
    for path in image_paths:
        mime, b64 = _encode_image(path)
        content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": content}],
        max_tokens=2000,
        response_format={"type": "json_object"},
    )
    raw = json.loads((response.choices[0].message.content or "{}").strip())
    return normalize_color_suggestions(raw.get("suggestions"), {e["index"] for e in entries})


def normalize_color_suggestions(raw_suggestions: object, valid_index: set[int]) -> dict[int, dict]:
    """モデルが返した色語提案を検証する。

    色語表に無い語は捨てる。配色ツールが認識できない語を提案しても記述を足す意味がなく、
    「提案どおり書いたのに拾われない」という一番たちの悪い結果になる。
    """
    out: dict[int, dict] = {}
    for item in raw_suggestions if isinstance(raw_suggestions, list) else []:
        if not isinstance(item, dict):
            continue
        try:
            index = int(item.get("index"))
        except (TypeError, ValueError):
            continue
        if index not in valid_index:
            continue
        words = [w for w in (item.get("color_words") or []) if w in _COLOR_WORD_JP]
        if words:
            out[index] = {"color_words": words, "note": str(item.get("note") or "").strip()}
    return out


def build_color_attr_proposal_md(
    audits: list[tuple[str, dict]],
    detections: dict[str, dict[int, dict]],
    common_words: list[str],
    before: dict[str, int] | None,
    model: str,
    command: str,
) -> str:
    """公式画像から読み取った色語で `#DesignAttr_Color` の追記案を組み立てる (Issue コメント用)。

    色の根拠は**公式画像**。`ColorPalette` の HEX は補完対象そのものなので根拠に使わず、
    「画像から読めた色が HEX 側にあるか」の突き合わせにだけ使う。
    """
    def _cell(text: str) -> str:
        return str(text).replace("|", "\\|").replace("\n", " ")

    def _attr_json(word: str) -> str:
        return (
            '`{"AttrLabel": "#DesignAttr_Color", '
            f'"value_JP": "{_COLOR_WORD_JP.get(word, word)}", "value_EN": "{word}"'
            "}`"
        )

    missing = [(label, e) for label, a in audits for e in a["missing_body_part"]]
    proposals = [
        (label, entry, detections[label][entry["index"]])
        for label, audit in audits
        for entry in audit["no_color_word"]
        if label in detections and entry["index"] in detections[label]
    ]

    lines = [
        "## `AppearanceDetail[].Attrs` 色情報の補完案（自動生成・画像根拠）",
        "",
        f"再検査日: {datetime.now():%Y-%m-%d} / 対象 {len(audits)} 件",
        "",
    ]
    if before:
        lines += [
            "### BodyPart 補完の効果",
            "",
            f"- BodyPart 欠落: **{before['missing']} 件 → {len(missing)} 件**"
            f"（{before['missing_chars']} キャラ → {len({l for l, _ in missing})} キャラ）",
            "",
            "残っているものは装飾・アクセント系（`four white buttons` / `orange accents` など）が中心で、",
            "部位を 1 つに決めにくいものが多い。末尾に一覧を置いた。",
            "",
        ]

    lines += [
        "### 色の根拠について",
        "",
        "**色語は公式画像から読み取っている。** `ColorPalette` の HEX は配色検知ツールが画像から",
        "起こした出力であり、いま補完しようとしている対象そのもの。HEX から色語を逆引きすると",
        "不完全な値を根拠に記述を書くことになるため、根拠は typedef `$palette.source` 宣言画像",
        "（設定原画・設定資料・コアフォルダ画像）に置いた。",
        f"読み取りには `{model}` を使用し、配色検知ツールが認識できる色語のみを選ばせている。",
        "",
        f"### 補完案（{len(proposals)} 件）",
        "",
        "色情報が入っていないエントリについて、画像から読み取った色。",
        "各行の `#` は `AppearanceDetail[]` のインデックス（1 始まり）。",
        "「読めた色」の先頭語を使って、そのエントリの `Attrs` へ次を足すと `AppliesTo` へ転記されるようになる。",
        "",
        "```json",
        '{ "AttrLabel": "#DesignAttr_Color", "value_JP": "<日本語>", "value_EN": "<色語>" }',
        "```",
        "",
        "| キャラ | # | 記述 | 読めた色 | 根拠 |",
        "|---|---|---|---|---|",
    ]
    for label, entry, found in proposals:
        words = found["color_words"]
        jp = "・".join(_COLOR_WORD_JP.get(w, w) for w in words)
        text = " / ".join(p.split(": ", 1)[-1] for p in str(entry["text"]).split(" / "))
        lines.append(
            f"| {_cell(label)} | {entry['index']} | {_cell(text)[:55]} |"
            f" {', '.join(f'`{w}`' for w in words)} ({jp}) | {_cell(found['note'])[:45]} |"
        )
    lines.append("")

    # 透過イラストからの実測色で ColorPalette に無いもの = そのまま追記できる欠落配色。
    missing_colors = [(label, c) for label, a in audits for c in a.get("missing_colors") or []]
    if missing_colors:
        lines += [
            f"### 創作 DB に無い配色（実測 HEX・{len(missing_colors)} 件）",
            "",
            "公式の透過イラスト（`$palette.source: artwork`）から**実測**した色のうち、",
            "`ColorPalette` のどの HEX とも一致しないもの（色距離 10 以内を同じ色とみなす）。",
            "抽出条件は上流 `patch-colorpalette.mjs --from-artwork` と同じで、共通造形色は除外済み。",
            "",
            "**確認してほしい点**: 純黒に近い色（`#010000` など）は輪郭線が彩度条件をすり抜けたもの、",
            "白に近い色は紙面・ハイライトの可能性がある。面積比が大きくても配色とは限らないので、",
            "`ColorPalette` へ入れる前に画像で確かめてほしい。",
            "",
            "| キャラ | 実測 HEX | 面積比 | 現在の ColorPalette |",
            "|---|---|---|---|",
        ]
        for label, color in missing_colors:
            audit = next(a for l, a in audits if l == label)
            existing = ", ".join(f"`{c['hex']}`" for c in audit["palette"]) or "—"
            lines.append(
                f"| {_cell(label)} | `{color['hex']}` | {color['ratio'] * 100:.1f}% | {existing} |"
            )
        lines.append("")

    # 画像から読めた色が ColorPalette 側に無い = HEX の取りこぼし候補。
    # 共通造形色 (肌色・毛色) は設計上 ColorPalette へ載らないので指摘対象から外す。
    common = set(common_words)
    gaps: list[tuple[str, str, list[str]]] = []
    for label, audit in audits:
        detected = {w for idx in detections.get(label, {}) for w in detections[label][idx]["color_words"]}
        if not detected:
            continue
        in_palette = {w for c in audit["palette"] for w in (c.get("colorWords") or [])}
        for word in sorted(detected - in_palette - common):
            gaps.append((label, word, [c["hex"] for c in audit["palette"]]))
    if gaps:
        lines += [
            f"### ColorPalette に見当たらない色（{len(gaps)} 件）",
            "",
            "画像から読み取れたのに、`ColorPalette` のどの HEX も該当しない色。",
            "**配色検知の取りこぼし候補**（抽出漏れ、または面積比の下限で落ちたもの）。",
            f"共通造形色に該当する色（{', '.join(f'`{w}`' for w in sorted(common)) or 'なし'}）は"
            "設計上 `ColorPalette` へ載らないため除外済み。",
            "",
            "| キャラ | 画像から読めた色 | 現在の ColorPalette |",
            "|---|---|---|",
        ]
        for label, word, hexes in gaps:
            lines.append(
                f"| {_cell(label)} | `{word}` ({_COLOR_WORD_JP.get(word, word)}) |"
                f" {', '.join(f'`{h}`' for h in hexes) or '—'} |"
            )
        lines.append("")

    if missing:
        lines += [
            "### 残っている BodyPart 欠落",
            "",
            "| キャラ | # | DesignElement | 記述 | 色語 |",
            "|---|---|---|---|---|",
        ]
        for label, entry in missing:
            words = ", ".join(sorted({h["word"] for h in entry["hints"]}))
            element = f"`{entry['element']}`" if entry["element"] else "—"
            text = " / ".join(p.split(": ", 1)[-1] for p in str(entry["text"]).split(" / "))
            lines.append(f"| {_cell(label)} | {entry['index']} | {element} | {_cell(text)[:90]} | {words} |")
        lines.append("")

    lines += [
        "---",
        "",
        "*色語は AI が公式画像から読み取った推定です。DB へ反映する前に確認してください。*",
        "*個別キャラの部位候補は `--num <N> --check coverage` で画像から提案できます。*",
        "",
        f"自動生成: `{command}` (100BeautiesLab_GeneratorsAI)",
        "",
    ]
    return "\n".join(lines)


# GitHub の Issue 本文・コメントの上限。超えると gh が 422 で弾く。
_GITHUB_BODY_LIMIT = 65536


def comment_issue(repo: str, issue: str, body_path: Path) -> str:
    size = len(body_path.read_text(encoding="utf-8"))
    if size > _GITHUB_BODY_LIMIT:
        raise SystemExit(
            f"[ERROR] 本文が GitHub の上限を超えています ({size} > {_GITHUB_BODY_LIMIT} 文字)。\n"
            f"        生成物: {body_path}\n"
            f"        --max-images を減らすか、対象を絞って分割してください。"
        )
    proc = subprocess.run(
        ["gh", "issue", "comment", str(issue), "-R", repo, "--body-file", str(body_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if proc.returncode != 0:
        raise SystemExit(f"[ERROR] gh issue comment 失敗: {(proc.stderr or '').strip()}")
    return (proc.stdout or "").strip()


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


def _char_label(record: dict, fallback: object = "") -> str:
    """Name_JP は "57(イズナ)" のように番号込みなので、Num を足すと二重になる。

    改行を含む名前 (別名併記の "34(サトシ)\\nサンジ" 等) があるため空白へ潰す。
    見出し・表・Issue タイトルのどこへ出しても崩れないようにするための正規化。
    """
    data = record.get("data") or {}
    label = str(data.get("Name_JP") or data.get("Name_EN") or data.get("Num") or fallback)
    return " ".join(label.split())


def detect_colors_for_records(
    targets: list[tuple[dict, str, dict]],
    model: str,
    max_images: int,
    workers: int,
) -> dict[str, dict[int, dict]]:
    """レコードごとに公式画像から色語を読み取る。API 待ちが支配的なのでスレッドで並べる。"""
    def _one(target: tuple[dict, str, dict]) -> tuple[str, dict[int, dict]]:
        record, label, audit = target
        # 一括では形態で絞らない (設定資料に両形態が載っているため)。
        images = collect_palette_source_images(record, None)[:max_images]
        try:
            return label, detect_colors_from_images(audit["no_color_word"], images, label, model)
        except Exception as err:  # 1 キャラの失敗で全体を止めない
            print(f"[WARN] {label}: 色の読み取りに失敗 ({type(err).__name__}: {err})")
            return label, {}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return dict(pool.map(_one, targets))


def run_bulk_coverage(args: argparse.Namespace, out_dir: Path, model: str) -> None:
    """作品内の全レコードを静的検査し、1 枚のレビューへまとめる。"""
    records = [
        r for r in load_manifest()
        if r.get("work_key") == args.work_key and r.get("has_appearance_detail")
    ]
    # 公式データを LLM へ渡すので、単体実行と同じ fail-closed ゲートを各レコードに通す。
    records = [
        r for r in records
        if apply_generation_gate(
            r, usage="image", num=(r.get("data") or {}).get("Num"), printer=print
        )[0]
    ]
    if not records:
        raise SystemExit(f"[ERROR] 対象レコードがありません: {args.work_key}")

    print(f"[all] {len(records)} 件の色語ヒントを取得中 (node)...")
    evidence, common_words = collect_color_hint_evidence(records, work_key=args.work_key)
    # 一括では形態で絞らない (BodyPart 欠落は形態に依らないため)。
    audits = [
        (_char_label(record), audit_coverage(ev, None))
        for record, ev in zip(records, evidence)
    ]

    missing = sum(len(a["missing_body_part"]) for _, a in audits)
    unbacked = sum(len(a["unbacked_hex"]) for _, a in audits)
    texts = sorted({e["text"] for _, a in audits for e in a["no_color_word"] if e["text"]})
    print(f"[all] BodyPart 欠落 {missing} 件 / 根拠なし色 {unbacked} 色 / 色語ヒント0 の記述 {len(texts)} 種")

    # 既存 Issue へのコメント: 公式画像を根拠に色語を読み取って補完案を出す。
    if args.comment:
        out_path = out_dir / f"{datetime.now():%Y%m%d}_color-attr-proposal_{str(args.work_key).lstrip('#')}.md"
        # 画像の読み取りは有料なので結果を隣へ残し、レポートの手直しは無料で回せるようにする。
        cache_path = out_path.with_suffix(".detections.json")
        if args.reuse_detections and cache_path.exists():
            detections = {k: {int(i): v for i, v in d.items()}
                          for k, d in json.loads(cache_path.read_text(encoding="utf-8")).items()}
            print(f"[all] 画像読み取り結果を再利用: {cache_path}")
        else:
            targets = [
                (record, label, audit)
                for record, (label, audit) in zip(records, audits)
                if audit["no_color_word"]
            ]
            print(f"[all] 公式画像から色語を読み取り中 ({len(targets)} キャラ, {model})...")
            detections = detect_colors_for_records(targets, model, args.max_images, args.workers)
            cache_path.write_text(
                json.dumps(detections, ensure_ascii=False, indent=1), encoding="utf-8"
            )
        found = sum(len(d) for d in detections.values())
        print(f"[all] 画像から色を読めたエントリ: {found} 件")

        proposal_command = (
            f"python -m src.tools.verify_appearance_detail --all --check coverage"
            f" --comment {args.comment}"
        )
        before = (
            {"missing": args.before_missing[0], "missing_chars": args.before_missing[1]}
            if args.before_missing
            else None
        )
        body = build_color_attr_proposal_md(
            audits, detections, common_words, before, model, proposal_command
        )
        out_path.write_text(body, encoding="utf-8")
        print(f"[all] 提案生成: {out_path}")
        if args.submit:
            print(f"[all] Issue #{args.comment} へ追記: {comment_issue(args.repo, args.comment, out_path)}")
        else:
            print(f"[all] 追記するには --submit を付ける (Issue #{args.comment})")
        return

    print(f"[all] 色語表に無い色語を抽出中 ({model}, 記述 {len(texts)} 種)...")
    unknown_words = extract_unknown_color_words(texts, model)
    print(f"[all] 色語候補: {len(set(w for ws in unknown_words.values() for w in ws))} 種")

    command = f"python -m src.tools.verify_appearance_detail --all --check coverage"
    body = build_bulk_coverage_md(
        audits, load_design_enums(), unknown_words, args.work_key, model, command
    )
    work_slug = str(args.work_key).lstrip("#")
    out_path = out_dir / f"{datetime.now():%Y%m%d}_coverage_all_{work_slug}.md"
    out_path.write_text(body, encoding="utf-8")
    print(f"[all] レビュー生成: {out_path}")

    if args.submit:
        title = (
            f"[AppearanceDetail 充足性・一括] {work_slug} {len(records)} 件"
            f" — BodyPart 欠落 {missing} / 根拠なし色 {unbacked}"
        )
        print(f"[all] Issue 送信: {submit_issue(args.repo, title, out_path)}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="AppearanceDetail を公式画像と照合し、レビュー Markdown を生成する"
    )
    ap.add_argument("--num", help="キャラクター番号 (例: 57, 2-alt)")
    ap.add_argument(
        "--all",
        action="store_true",
        help="作品内の AppearanceDetail を持つ全レコードを一括検査する (--check coverage 専用)",
    )
    ap.add_argument(
        "--check",
        default="match",
        choices=["match", "coverage"],
        help="match=記述と画像の照合 / coverage=配色検知ツール向けの BodyPart・DesignElement 充足検査",
    )
    ap.add_argument("--form", default="corefolder", choices=[*_FORMS, "both"])
    ap.add_argument("--work-key", default="#Works_NumberTales")
    # 2 枚だと humanoid でバストアップ + 尾構造図に偏り、全身の設定画が入らず unclear が増える。
    ap.add_argument("--max-images", type=int, default=3, help="Vision へ渡す公式画像の枚数")
    ap.add_argument("--repo", default=DEFAULT_REPO, help="レビュー送付先リポジトリ")
    ap.add_argument(
        "--comment",
        help="新規 Issue を立てず、指定 Issue 番号へ色情報の補完案をコメント追記する (--all 用)",
    )
    ap.add_argument("--workers", type=int, default=4, help="一括の画像読み取りの並列数")
    ap.add_argument(
        "--reuse-detections",
        action="store_true",
        help="同日の画像読み取り結果 (.detections.json) があれば再利用する (レポート手直し用)",
    )
    ap.add_argument(
        "--before-missing",
        nargs=2,
        type=int,
        metavar=("件数", "キャラ数"),
        help="前回の BodyPart 欠落数。指定すると補完の効果を提案コメントに載せる",
    )
    ap.add_argument("--submit", action="store_true", help="生成したレビューを Issue として送る (既定は生成のみ)")
    ap.add_argument("--out-dir", default=str(_PROJECT_ROOT / "_ideas" / "db-reviews"))
    args = ap.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("[ERROR] OPENAI_API_KEY が未設定です (.env を確認してください)")
    if args.all and args.check != "coverage":
        raise SystemExit("[ERROR] --all は --check coverage でのみ使えます")
    if not args.all and not args.num:
        raise SystemExit("[ERROR] --num または --all を指定してください")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    model = os.environ.get("GPT_MODEL", "gpt-4o")

    if args.all:
        run_bulk_coverage(args, out_dir, model)
        return

    record = find_character(args.num, work_key=args.work_key)
    if not record:
        raise SystemExit(f"[ERROR] キャラクターが見つかりません: num={args.num}")

    # 公式画像を LLM へ送るため、生成入口と同じ fail-closed ゲートを通す。
    proceed, _gate = apply_generation_gate(record, usage="image", num=args.num, printer=print)
    if not proceed:
        raise SystemExit(1)

    data = record.get("data") or {}
    char_label = _char_label(record, args.num)
    forms = _FORMS if args.form == "both" else (args.form,)

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
        # coverage は静的検査が本体なので、画像が無くても続行する (部位候補の提案だけ省く)。
        if not image_paths and args.check == "match":
            print(f"[SKIP] {form}: 照合できるローカル公式画像がありません")
            continue

        print(f"[{form}] 使用する公式画像 ({source_label}): {', '.join(p.name for p in image_paths)}")
        command = (
            f"python -m src.tools.verify_appearance_detail --num {args.num}"
            f" --check {args.check} --form {form}"
        )

        if args.check == "coverage":
            audit = audit_coverage(
                collect_color_hint_evidence([record], work_key=args.work_key)[0][0], form
            )
            print(
                f"[{form}] BodyPart 欠落 {len(audit['missing_body_part'])} 件"
                f" / 根拠なし色 {len(audit['unbacked_hex'])} 色"
                f" / 色語ヒント0 {len(audit['no_color_word'])} 件"
            )
            enums = load_design_enums()
            # 不足が無ければ Vision を呼ばない (提案する対象が無いので課金する意味がない)。
            suggestions = suggest_body_parts(audit, enums, image_paths, char_label, form, model)
            body = build_coverage_md(
                char_label, form, audit, enums, suggestions, image_paths, model, command
            )
            out_path = out_dir / f"{datetime.now():%Y%m%d}_coverage_num{_num_slug(data.get('Num'))}_{form}.md"
            out_path.write_text(body, encoding="utf-8")
            print(f"[{form}] レビュー生成: {out_path}")
            if args.submit:
                title = (
                    f"[AppearanceDetail 充足性] {char_label} / {form}"
                    f" — BodyPart 欠落 {len(audit['missing_body_part'])}"
                    f" / 根拠なし色 {len(audit['unbacked_hex'])}"
                )
                print(f"[{form}] Issue 送信: {submit_issue(args.repo, title, out_path)}")
            continue

        entry_lines = [format_entry(i, e) for i, e in enumerate(entries, 1)]
        print(f"[{form}] {len(entry_lines)} 件を {len(image_paths)} 枚の公式画像と照合中 ({model})...")
        results = analyze(entry_lines, image_paths, char_label, form, model)
        counts = summarize(results)
        print(f"[{form}] match {counts['match']} / mismatch {counts['mismatch']} / unclear {counts['unclear']}")

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
