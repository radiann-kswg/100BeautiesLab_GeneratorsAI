"""実行の記録と完成画像を GCS に残し、手元に無い実行を改稿の起点として戻す流れの回帰テスト。GCS は呼ばない。"""
from __future__ import annotations

import json
from pathlib import Path, PurePosixPath

import pytest

from src.mcp_server import output_sink
from src.utils import iterate

RUN = "20261120_150049_pipeline_corefolder_num57"
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32


class _Blob:
    def __init__(self, bucket, name):
        self.bucket, self.name = bucket, name

    @property
    def size(self):
        return len(self.bucket.store[self.name])

    def download_as_bytes(self):
        return self.bucket.store[self.name]

    def upload_from_filename(self, path):
        self.bucket.store[self.name] = Path(path).read_bytes()


class _Bucket:
    def __init__(self):
        self.store: dict[str, bytes] = {}

    def blob(self, key):
        return _Blob(self, key)

    def get_blob(self, key):
        return _Blob(self, key) if key in self.store else None

    def list_blobs(self, prefix=None):
        return [_Blob(self, key) for key in self.store if key.startswith(prefix or "")]


def _write_run(base: Path, recorded_root: str) -> Path:
    """完成画像 2 枚と Stage 1 の土台を持つ実行フォルダーを作る。記録のパスは ``recorded_root`` 起点で書く。"""
    run_dir = base / RUN[:8] / RUN
    finals = [f"stage5_final/synth/a/num057_corefolder_0{i}.png" for i in (1, 2)]
    for rel in finals:
        (run_dir / rel).parent.mkdir(parents=True, exist_ok=True)
        (run_dir / rel).write_bytes(PNG + rel.encode())
    (run_dir / "stage1_prompt").mkdir()
    (run_dir / "stage1_prompt" / "prompt_base_gemini.txt").write_text("STAGE1 BASE", encoding="utf-8")
    (run_dir / "stage3_rough").mkdir()
    (run_dir / "stage3_rough" / "rough.png").write_bytes(PNG)
    summary = {"num": 57, "form": "corefolder", "status": "ok", "scene_used": "窓辺",
               "stage5_paths": {"all": [f"{recorded_root}{rel}" for rel in finals] + ["C:/elsewhere/other.png"]}}
    (run_dir / "pipeline_summary.json").write_text(json.dumps(summary, ensure_ascii=False), encoding="utf-8")
    return run_dir


def test_recorded_paths_become_relative_to_the_run_folder():
    assert output_sink.run_relative(f"output/20261120/{RUN}/stage5_final/a.png", RUN) == PurePosixPath("stage5_final/a.png")
    assert output_sink.run_relative(f"C:\\work\\output\\20261120\\{RUN}\\stage5_final\\a.png", RUN) == PurePosixPath(
        "stage5_final/a.png")
    assert output_sink.run_relative("output/20261120/other_run/a.png", RUN) is None       # 実行フォルダーの外
    assert output_sink.run_relative(f"output/{RUN}/../secret.png", RUN) is None
    assert output_sink.run_relative(f"output/{RUN}", RUN) is None
    assert output_sink.run_relative(f"output/{RUN}/C:/Windows/a.png", RUN) is None


def test_run_is_stored_then_restored_as_an_iterate_source(tmp_path, monkeypatch):
    bucket = _Bucket()
    monkeypatch.setattr(output_sink, "_bucket", lambda: bucket)
    monkeypatch.delenv("GCS_PREFIX", raising=False)
    server_side = _write_run(tmp_path / "server", f"C:\\srv\\output\\{RUN[:8]}\\{RUN}\\")

    stored = output_sink.store_run(str(server_side))
    prefix = f"numbertales/runs/{RUN}/"
    assert stored["note"] == "" and stored["stored"][-1] == prefix + "pipeline_summary.json"      # 記録は最後に置く
    assert sorted(bucket.store) == sorted(prefix + rel for rel in (
        "pipeline_summary.json", "stage1_prompt/prompt_base_gemini.txt",
        "stage5_final/synth/a/num057_corefolder_01.png", "stage5_final/synth/a/num057_corefolder_02.png"))
    (row,) = output_sink.list_stored_runs()
    assert row == {"run_id": RUN, "status": "ok", "nums": [57], "forms": ["corefolder"], "scene_used": "窓辺",
                   "final_count": 2}
    assert "pipeline_summary.json がありません" in output_sink.store_run(str(tmp_path / "missing"))["note"]

    # 手元に無い実行は、出力先が手元の設定では探しに行かない。GCS か Drive の設定なら戻す
    fresh = tmp_path / "fresh"
    monkeypatch.setenv("OUTPUT_BASE_DIR", str(fresh))
    monkeypatch.setenv("OUTPUT_SINK", "local")
    with pytest.raises(FileNotFoundError):
        iterate.resolve_iterate_source(RUN)
    monkeypatch.setenv("OUTPUT_SINK", "drive")
    image, run_dir = iterate.resolve_iterate_source(RUN)
    assert run_dir == fresh / RUN[:8] / RUN and image == run_dir / "stage5_final/synth/a/num057_corefolder_01.png"
    assert image.read_bytes().startswith(PNG)
    assert (run_dir / "stage1_prompt" / "prompt_base_gemini.txt").read_text(encoding="utf-8") == "STAGE1 BASE"
    assert not (run_dir / "stage3_rough").exists()                         # 戻すのは、起点に要るものだけ
    # 二度目は手元の実行を使う（GCS を読まない）
    monkeypatch.setattr(output_sink, "restore_run", lambda *a, **k: pytest.fail("手元にある実行を取り直した"))
    assert iterate.resolve_iterate_source(RUN)[0] == image
    # 実行フォルダーのパスを渡しても、記録にある完成画像を起点にする
    assert iterate.resolve_iterate_source(str(run_dir))[0] == image

    from src.pipeline import image_pipeline
    assert image_pipeline._previous_base_prompt(image) == "STAGE1 BASE"


def test_unknown_run_ids_and_other_prefixes_are_not_restored(tmp_path, monkeypatch):
    bucket = _Bucket()
    bucket.store[f"shapechange/runs/{RUN}/pipeline_summary.json"] = b"{}"
    monkeypatch.setattr(output_sink, "_bucket", lambda: bucket)
    monkeypatch.delenv("GCS_PREFIX", raising=False)
    monkeypatch.setenv("OUTPUT_BASE_DIR", str(tmp_path))
    monkeypatch.setenv("OUTPUT_SINK", "gcs")
    assert output_sink.restore_run(RUN, tmp_path) is None                  # ほかの接頭辞の実行は読まない
    for value in (RUN, "../" + RUN, "not-a-run", f"output/{RUN}"):
        with pytest.raises(FileNotFoundError):
            iterate.resolve_iterate_source(value)
    assert list(tmp_path.iterdir()) == []


def test_restore_requires_the_first_final_image_but_not_optional_prompt(tmp_path, monkeypatch):
    bucket = _Bucket()
    prefix = f"numbertales/runs/{RUN}/"
    first = "stage5_final/synth/a/num057_corefolder_01.png"
    summary = {"stage5_paths": {"all": [f"output/{RUN}/{first}"]}}
    bucket.store[prefix + "pipeline_summary.json"] = json.dumps(summary).encode()
    monkeypatch.setattr(output_sink, "_bucket", lambda: bucket)

    assert output_sink.restore_run(RUN, tmp_path) is None
    assert list(tmp_path.iterdir()) == []

    bucket.store[prefix + first] = PNG
    restored = output_sink.restore_run(RUN, tmp_path)
    assert restored == tmp_path / RUN[:8] / RUN
    assert (restored / first).read_bytes() == PNG
    assert (restored / "pipeline_summary.json").is_file()
    assert not (restored / "stage1_prompt" / "prompt_base_gemini.txt").exists()
