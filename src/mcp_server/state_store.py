"""インスタンスが入れ替わっても残す、小さな状態の置き場。

Cloud Run は、生成のジョブが裏で動いていてもインスタンスを入れ替えることがある（2026-11-21。最後のリクエストから
3 分後に入れ替わり、サインインの状態とジョブの記録が消えた）。ここでは、サインインの状態（``auth.py``）と
ジョブの記録（``jobs.py``）を、GCS のバケット（中間画像と同じバケットの、接頭辞の下の ``state/``）へ JSON で 1 件ずつ置く。

- 置くのは、HTTP で公開するサーバー（``MCP_ISSUER_URL`` があり、``GCS_BUCKET`` が設定されているとき）だけ。
  手元の stdio や VM では何も保存しない（``server.py`` が :func:`default_store` を呼ぶ）。
- 保存や読み出しに失敗しても、サーバーは止めない（メモリー上の状態だけで動き続ける）。
- 名前に使えるのは英数字と ``-`` ``_`` だけ。トークンのような秘密の値は、呼ぶ側がハッシュにしてから名前に使う。
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Protocol

from src.mcp_server import output_sink

_NAME = re.compile(r"[A-Za-z0-9_-]{1,128}")
STATE_DIR = "state"


class Store(Protocol):
    def put(self, kind: str, name: str, data: dict[str, Any]) -> bool: ...
    def get(self, kind: str, name: str) -> dict[str, Any] | None: ...
    def delete(self, kind: str, name: str) -> None: ...


class MemoryStore:
    """プロセスの中だけの置き場（テスト用。別のインスタンスに見立てた受け渡しを確かめる）。"""

    def __init__(self) -> None:
        self.items: dict[tuple[str, str], str] = {}

    def put(self, kind: str, name: str, data: dict[str, Any]) -> bool:
        if not (_NAME.fullmatch(kind) and _NAME.fullmatch(name)):
            return False
        self.items[(kind, name)] = json.dumps(data, ensure_ascii=False)
        return True

    def get(self, kind: str, name: str) -> dict[str, Any] | None:
        raw = self.items.get((kind, name))
        return json.loads(raw) if raw is not None else None

    def delete(self, kind: str, name: str) -> None:
        self.items.pop((kind, name), None)


class GcsStore:
    """GCS の ``<接頭辞>/state/<種類>/<名前>.json`` に置く。"""

    def __init__(self) -> None:
        self._bucket: Any = None

    def _blob(self, kind: str, name: str) -> Any:
        if not (_NAME.fullmatch(kind) and _NAME.fullmatch(name)):
            raise ValueError("名前に使えない文字があります")
        if self._bucket is None:
            self._bucket = output_sink._bucket()
        return self._bucket.blob(f"{output_sink._gcs_prefix()}/{STATE_DIR}/{kind}/{name}.json")

    def put(self, kind: str, name: str, data: dict[str, Any]) -> bool:
        try:
            self._blob(kind, name).upload_from_string(
                json.dumps(data, ensure_ascii=False), content_type="application/json")
            return True
        except Exception as err:  # noqa: BLE001 - 保存できなくても、メモリー上の状態で動き続ける
            print(f"[WARN] 状態を保存できませんでした（{kind}）: {output_sink._err_detail(err)}")
            return False

    def get(self, kind: str, name: str) -> dict[str, Any] | None:
        try:
            blob = self._blob(kind, name)
            if not blob.exists():
                return None
            data = json.loads(blob.download_as_bytes())
            return data if isinstance(data, dict) else None
        except Exception as err:  # noqa: BLE001
            print(f"[WARN] 状態を読み出せませんでした（{kind}）: {output_sink._err_detail(err)}")
            return None

    def delete(self, kind: str, name: str) -> None:
        try:
            self._blob(kind, name).delete()
        except Exception:  # noqa: BLE001 - すでに無い場合を含め、消せなくても困らない
            pass


def default_store() -> Store | None:
    """バケットが設定されていれば GCS の置き場、無ければ None（何も保存しない）。"""
    return GcsStore() if os.getenv(output_sink.ENV_GCS_BUCKET, "").strip() else None
