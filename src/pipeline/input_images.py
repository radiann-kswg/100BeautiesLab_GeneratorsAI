"""pipeline/input_images.py — 依頼者が渡す入力画像（加筆の起点・赤入れ・構図参考・参考画像）。
Copyright © RadianN_kswg — CC BY-NC 4.0

役割ごとに、枚数の上限と渡すステージが決まっている（docs/usage-iterate.md「入力画像」）。

| 役割 | 意味 | 枚数 | Stage 3 ラフ | Stage 4 検査 | Stage 5 合成 |
| --- | --- | --- | --- | --- | --- |
| ``base`` | 加筆の起点 | 1 | ○（先頭） | × | ○ |
| ``markup`` | 加筆の起点に描き込んだ赤入れ（起点が必須） | 1 | ○ | ○ | × |
| ``composition`` | 構図参考。グレースケールにして渡す | 1 | ○ | × | × |
| ``reference`` | 生成画像と関係のない参考。``note``（用途）が必須 | 3 | ○ | × | ○ |

合同生成では、キャラクターごとのラフと検査には渡さず、全員を 1 枚にまとめる Stage 5 でだけ使う。

受け付ける出所（``provenance``）は、このパイプラインの生成結果と依頼者自身の作品だけ。
置き場は、CLI では出力フォルダーか ``references/`` の中（``path``）、コネクタでは GCS の
自分の接頭辞の下（``object_key``）に限る。
"""

from __future__ import annotations

import hashlib
import json
from io import BytesIO
from pathlib import Path
from typing import Any, Callable

from src.utils.image_io import detect_image_format

MAX_BYTES = 10 * 1024 * 1024
MAX_NOTE = 200
ASPECT_TOLERANCE = 0.02
SUFFIXES = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}
PROVENANCES = {
    "own_generated": "このパイプラインの生成結果",
    "own_work": "依頼者自身の作品",
    "own_photo": "依頼者自身が撮った写真",
}
#: 役割 → (呼び名, 枚数の上限, 渡すステージ)。並びは参照に添付する順。
ROLES: dict[str, tuple[str, int, tuple[int, ...]]] = {
    "base": ("加筆の起点", 1, (3, 5)),
    "markup": ("赤入れ（加筆の起点への指示書き）", 1, (3, 4)),
    "composition": ("構図参考（グレースケール）", 1, (3,)),
    "reference": ("参考画像", 3, (3, 5)),
}
#: 合同生成で入力画像を渡すステージ（全員を 1 枚にまとめる合成だけ）。
JOINT_STAGES = (5,)
#: 役割 → 生成モデルへ添付するとき、画像の直前に挟むラベル（参考画像は ``label()`` が用途を入れる）。
_LABELS = {
    "base": "加筆の起点: 構図と良い点を引き継ぐ起点。色・特徴・作風の正典ではない。",
    "markup": "赤入れ（加筆の起点への指示書き）: 赤い印が指す場所を直す。赤い印と指示の文字そのものは描かない。",
    "composition": "構図参考（グレースケール）: ポーズ・配置・画角だけを借りる。色・画風・衣装・顔立ち・外見は写さない。",
}

Locate = Callable[[str], Path]
Fetch = Callable[[str], bytes]


def label(image: dict[str, Any]) -> str:
    """画像の直前に挟む役割のラベル。"""
    if image["kind"] == "reference":
        return f"参考画像（用途: {image['note']}）: この用途にだけ使う。キャラクターの外見は公式原典と設定が正しい。"
    return _LABELS[image["kind"]]


def for_stage(images: list[dict[str, Any]] | None, stage: int) -> list[dict[str, Any]]:
    """そのステージへ渡す入力画像だけを、添付の順（``ROLES`` の並び）で返す。"""
    order = list(ROLES)
    kept = [image for image in images or [] if stage in image.get("stages", ())]
    return sorted(kept, key=lambda image: order.index(image["kind"]))


def split(images: list[dict[str, Any]] | None, stage: int) -> tuple[dict[str, Any] | None, list[dict[str, Any]], list[dict[str, Any]]]:
    """そのステージの入力画像を (加筆の起点, 公式画像より前に添付するもの, 後ろに添付するもの) に分ける。"""
    staged = for_stage(images, stage)
    base = next((image for image in staged if image["kind"] == "base"), None)
    leading = [image for image in staged if image["kind"] in ("markup", "composition")]
    trailing = [image for image in staged if image["kind"] == "reference"]
    return base, leading, trailing


def labels(images: list[dict[str, Any]]) -> dict[str, str]:
    """書き出し済みの入力画像の {パス: ラベル}。"""
    return {str(image["path"]): label(image) for image in images if image.get("path")}


def prompt_block(images: list[dict[str, Any]] | None, stage: int, *, has_revisions: bool = False,
                 has_iterate_source: bool = False, synthesis: bool = False) -> str:
    """そのステージのプロンプトに添える、入力画像の使い方。渡す画像が無ければ空文字。

    画像には ``label()`` のラベルが付くので、ここでは役割の名前で呼ぶ（添付の番号は生成側が振る）。
    ``has_iterate_source`` は、役割 base の画像が無く、改稿の起点（前回の生成結果）が先頭に付く場合。
    ``synthesis`` は、検査を通ったラフ案をまとめる合成（単体の Stage 5）。直した点はラフ案にある。
    """
    staged = for_stage(images, stage)
    if not staged:
        return ""
    kinds = {image["kind"] for image in staged}
    lines = [
        "[入力画像の扱い]",
        "- 依頼者が渡した画像には、画像ごとに役割のラベルを付けてある。ラベルに書いた使い方だけに従う。",
        "- キャラクターの外見（顔立ち・髪・衣装・配色・識別要素）は公式原典と設定資料が正しい。"
        "入力画像と食い違うときは、公式原典と設定資料を採る。",
    ]
    if "base" in kinds:
        if synthesis:
            rest = "ぐ。直した点は、添付のラフ案に従う。"
        elif "markup" in kinds:
            rest = "ぎ、赤入れの指示" + ("と [修正指示] " if has_revisions else "") + "だけを反映する。"
        elif has_revisions:
            rest = "ぎ、[修正指示] だけを反映する。"
        else:
            rest = "ぎ、下の作画指定に合うように描き直す。"
        lines.append("- 加筆の起点: 構図と良い点を引き継" + rest)
    if "markup" in kinds:
        target = "加筆の起点" if "base" in kinds or not has_iterate_source else "起点画像（前回生成）"
        lines += [
            f"- 赤入れ: {target}に赤で指示を描き込んだもの。赤い線・丸・矢印・短い書き込みが指す場所を、"
            "その指示のとおりに直す。赤い印と指示の文字そのものは絵に描かない。",
            "The marked-up image is a copy of the starting image with instructions drawn in red: fix what the red"
            " marks point at, and never draw the red marks or the handwritten notes themselves.",
        ]
    if "composition" in kinds:
        lines += [
            "- 構図参考: ポーズ・配置・画角だけを借りる。色を抜いてあるので、色・画風・衣装・顔立ち・"
            "キャラクターの外見は写さない。",
            "The greyscale composition guide lends only its pose, placement and camera angle; take no colours,"
            " style, outfit or character design from it.",
        ]
    if "reference" in kinds:
        lines.append("- 参考画像: ラベルに書いた用途にだけ使う。それ以外の要素（構図・キャラクターの外見・文字・ロゴ）は写さない。")
    return "\n".join(lines)


def parse_spec(value: str | list | None) -> list[dict[str, Any]]:
    """``--images`` の値（JSON の配列、またはそれを書いた .json ファイルのパス）か、辞書のリストを読む。"""
    if isinstance(value, list):
        items = value
    else:
        text = (value or "").strip()
        if not text:
            return []
        if not text.startswith("["):
            file = Path(text).expanduser()
            if not file.is_file():
                raise ValueError(f"--images は JSON の配列か、それを書いたファイルを指定してください: {value}")
            text = file.read_text(encoding="utf-8-sig")
        try:
            items = json.loads(text)
        except json.JSONDecodeError as err:
            raise ValueError(f"--images を JSON として読めません: {err}") from err
    if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
        raise ValueError('images は [{"role": …, "path" か "object_key": …, "provenance": …}] の形で指定してください。')
    return items


def dimensions(data: bytes) -> tuple[int, int]:
    try:
        from PIL import Image
    except ImportError as err:
        raise ValueError("入力画像の確認には Pillow が必要です: pip install -r requirements.txt") from err
    try:
        with Image.open(BytesIO(data)) as image:
            return image.size
    except Exception as err:  # noqa: BLE001 — 壊れた画像は理由を問わず受け付けない
        raise ValueError("画像として開けません。") from err


def _grayscale(data: bytes) -> bytes:
    """白地に重ねてからグレースケールの PNG にする（透過部分が黒くならないように）。"""
    from PIL import Image

    with Image.open(BytesIO(data)) as image:
        rgba = image.convert("RGBA")
        canvas = Image.new("RGBA", rgba.size, "white")
        canvas.alpha_composite(rgba)
        buffer = BytesIO()
        canvas.convert("L").save(buffer, format="PNG")
        return buffer.getvalue()


def locate_local(raw: str, output_base: Path | str | None = None) -> Path:
    """CLI の ``path`` を検証する。受け付けるのは、出力フォルダーか ``references/`` の中のファイルだけ。"""
    from src.utils.paths import default_output_base

    path = Path(raw).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"images の path のファイルが見つかりません: {raw}")
    roots = [Path(output_base or default_output_base()).resolve(), references_dir().resolve()]
    if not any(path.is_relative_to(root) for root in roots):
        raise ValueError(
            f"images の path は、出力フォルダーか references/ の中のファイルを指定してください: {raw}\n"
            "  出典・作者・権利条件を確かめた自分の素材を references/ に置いてから指定します。")
    return path


def references_dir() -> Path:
    """手元の素材を置くフォルダー（リポジトリ直下の ``references/``。Git の追跡対象外）。"""
    return Path(__file__).resolve().parents[2] / "references"


def fetch_object(key: str) -> bytes:
    """コネクタが GCS に受け取った入力画像を読む（自分の接頭辞の下だけ。出力シンクが確かめる）。"""
    from src.mcp_server import output_sink

    return output_sink.read_object(key, MAX_BYTES)


def resolve(
    items: list[dict[str, Any]],
    *,
    locate: Locate = locate_local,
    fetch: Fetch | None = fetch_object,
    iterate_base: Path | None = None,
    joint: bool = False,
) -> list[dict[str, Any]]:
    """指定を検証して参照の形にする。生成 API は呼ばない（GCS の読み取りだけ行う）。

    ``locate`` は ``path`` を検証済みの場所へ解決する関数、``fetch`` は ``object_key`` の中身を返す関数。
    ``iterate_base`` は改稿の起点の画像（赤入れの縦横比の照合に使う）。``joint`` は合同生成。
    返す参照の ``path`` は ``materialize`` が実行フォルダーへ書き出すまで None。
    """
    images: list[dict[str, Any]] = []
    for index, item in enumerate(items, start=1):
        where = f"images[{index}]"
        role, provenance = str(item.get("role") or ""), str(item.get("provenance") or "")
        note = " ".join(str(item.get("note") or "").split())
        if role not in ROLES:
            raise ValueError(f"{where}: role は {' / '.join(ROLES)} のいずれかを指定してください: {role or '(未指定)'}")
        if provenance not in PROVENANCES:
            raise ValueError(f"{where}: provenance（出所）は毎回必要です。{' / '.join(PROVENANCES)} のいずれか: "
                             f"{provenance or '(未指定)'}\n  受け付けるのは、このパイプラインの生成結果と依頼者自身の作品だけです。")
        if role == "reference" and not note:
            raise ValueError(f"{where}: 役割 reference には note（何の参考にするか）が必要です。")
        if len(note) > MAX_NOTE:
            raise ValueError(f"{where}: note は {MAX_NOTE} 文字までです。")
        path, key = item.get("path"), item.get("object_key")
        if bool(path) == bool(key):
            raise ValueError(f"{where}: path（出力フォルダーか references/ の中）か object_key（GCS）のどちらか一方を指定してください。")
        if key:
            if fetch is None:
                raise ValueError(f"{where}: object_key を読める GCS の設定がありません。")
            data, source = fetch(str(key)), {"object_key": str(key)}
        else:
            file = locate(str(path))
            if file.stat().st_size > MAX_BYTES:
                raise ValueError(f"{where}: 1 枚 {MAX_BYTES // (1024 * 1024)}MB までです: {path}")
            data, source = file.read_bytes(), {"path": str(file)}
        if len(data) > MAX_BYTES:
            raise ValueError(f"{where}: 1 枚 {MAX_BYTES // (1024 * 1024)}MB までです。")
        detected = detect_image_format(data[:16])
        if not detected or detected[1] not in SUFFIXES:
            raise ValueError(f"{where}: PNG・JPEG・WebP の画像だけを受け付けます（拡張子ではなく中身で判定します）。")
        try:
            width, height = dimensions(data)
        except ValueError as err:
            raise ValueError(f"{where}: {err}") from err
        images.append({
            "path": None, "kind": role, "stages": JOINT_STAGES if joint else ROLES[role][2], "note": note,
            "provenance": provenance, "source": source, "data": data, "mime": detected[1],
            "width": width, "height": height, "sha256": hashlib.sha256(data).hexdigest(),
        })

    for role, (name, limit, _) in ROLES.items():
        count = sum(1 for image in images if image["kind"] == role)
        if count > limit:
            raise ValueError(f"役割 {role}（{name}）は {limit} 枚までです（{count} 枚指定されています）。")
    base = next((image for image in images if image["kind"] == "base"), None)
    markup = next((image for image in images if image["kind"] == "markup"), None)
    if markup:
        if base:
            base_size = (base["width"], base["height"])
        elif iterate_base:
            base_size = dimensions(Path(iterate_base).read_bytes())
        else:
            raise ValueError("役割 markup（赤入れ）には、加筆の起点（役割 base の画像か、改稿の起点の実行）が必要です。")
        base_ratio, markup_ratio = base_size[0] / base_size[1], markup["width"] / markup["height"]
        if abs(markup_ratio - base_ratio) / base_ratio >= ASPECT_TOLERANCE:
            raise ValueError(
                f"赤入れの画像の縦横比が加筆の起点と {ASPECT_TOLERANCE:.0%} 以上違います"
                f"（起点 {base_size[0]}×{base_size[1]}、赤入れ {markup['width']}×{markup['height']}）。"
                "起点の画像にそのまま描き込んだものを渡してください。")
    return images


def describe(image: dict[str, Any]) -> dict[str, Any]:
    """記録と事前確認に出す、入力画像 1 枚ぶんの要約（中身は含めない）。"""
    return {
        "role": image["kind"], "note": image["note"], "provenance": image["provenance"], "source": image["source"],
        "bytes": len(image["data"]), "width": image["width"], "height": image["height"], "sha256": image["sha256"],
        "stages": list(image["stages"]), "grayscale": image["kind"] == "composition",
    }


def materialize(images: list[dict[str, Any]], run_dir: Path) -> list[dict[str, Any]]:
    """入力画像を実行フォルダーの inputs/ に書き出して参照の ``path`` を埋め、記録用の要約を返す。

    構図参考はここでグレースケールにする（色・画風を参考にさせないため）。
    """
    records: list[dict[str, Any]] = []
    serial: dict[str, int] = {}
    for image in images:
        kind = image["kind"]
        serial[kind] = serial.get(kind, 0) + 1
        data, suffix = image["data"], SUFFIXES[image["mime"]]
        if kind == "composition":
            data, suffix = _grayscale(data), ".png"
        target = Path(run_dir) / "inputs" / f"{kind}_{serial[kind]:02d}{suffix}"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        image["path"] = target
        records.append({**describe(image), "file": target.relative_to(run_dir).as_posix()})
    return records
