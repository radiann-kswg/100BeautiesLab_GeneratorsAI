"""
sdxl/client.py — GCE VM への SSH バッチ推論クライアント (B-1方式)
Copyright © RadianN_kswg — CC BY-NC 4.0

生成毎に VM を起動 → 推論スクリプト実行 → 結果回収 → VM 停止する。
gcloud on Windows の既知の癖 (NumberTales-GeneratorsAI の 2026-07-14 ワークログ由来):
  - リモートパスは `~` 不可。絶対パスで書く。
  - 初回ホスト鍵確認のハング対策に `--strict-host-key-checking=no --quiet` を付ける。
  - PowerShell のクォート破壊対策として、shell=False の引数リストで subprocess を呼ぶ。

.env (docs/setup.md 参照):
  SDXL_GCP_PROJECT      (default: claude-radiannkswg)
  SDXL_VM_NAME          (default: lora-l4-trial)
  SDXL_VM_ZONE          (default: asia-east1-b)
  SDXL_REMOTE_WORKDIR   (default: /home/s-chi/sdxl-infer)
  SDXL_REMOTE_BASE_MODEL  VM 上の Illustrious-XL チェックポイントの絶対パス
  SDXL_REMOTE_LORA        VM 上の LoRA 重みの絶対パス (既定はエポック4)
  SDXL_LORA_SCALE       (default: 0.8)
  SDXL_REMOTE_PYTHON    推論に使う VM 上の python 実行ファイル
                        (default: python3。diffusers 入りの venv を指定推奨。
                         例: /home/s-chi/sd-scripts/venv/bin/python)
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

_SSH_FLAGS = ["--strict-host-key-checking=no", "--quiet"]


def _cfg(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def _gcloud_bin() -> str:
    for name in ("gcloud", "gcloud.cmd"):
        found = shutil.which(name)
        if found:
            return found
    return "gcloud"


class SdxlVmClient:
    """VM 起動〜推論〜回収〜停止のオーケストレーション。"""

    def __init__(self, dry_run: bool = False) -> None:
        self.dry_run = dry_run
        self.project = _cfg("SDXL_GCP_PROJECT", "claude-radiannkswg")
        self.vm_name = _cfg("SDXL_VM_NAME", "lora-l4-trial")
        self.zone = _cfg("SDXL_VM_ZONE", "asia-east1-b")
        self.workdir = _cfg("SDXL_REMOTE_WORKDIR", "/home/s-chi/sdxl-infer")
        self.base_model = _cfg("SDXL_REMOTE_BASE_MODEL")
        self.lora_path = _cfg("SDXL_REMOTE_LORA")
        self.lora_scale = float(_cfg("SDXL_LORA_SCALE", "0.8"))
        self.remote_python = _cfg("SDXL_REMOTE_PYTHON", "python3")
        self._started_by_us = False

    # ── low-level ──────────────────────────────

    def _run(self, args: list[str], timeout: int = 300) -> subprocess.CompletedProcess:
        cmd = [_gcloud_bin(), *args, f"--project={self.project}"]
        if self.dry_run:
            print(f"[sdxl:dry-run] {' '.join(cmd)}")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        return subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout, check=False
        )

    def _ssh(self, remote_cmd: str, timeout: int = 1800) -> subprocess.CompletedProcess:
        return self._run(
            ["compute", "ssh", self.vm_name, f"--zone={self.zone}", *_SSH_FLAGS,
             f"--command={remote_cmd}"],
            timeout=timeout,
        )

    def _scp(self, src: str, dest: str, timeout: int = 600) -> subprocess.CompletedProcess:
        return self._run(
            ["compute", "scp", "--recurse", src, dest, f"--zone={self.zone}", *_SSH_FLAGS],
            timeout=timeout,
        )

    # ── VM lifecycle ───────────────────────────

    def vm_status(self) -> str:
        result = self._run(
            ["compute", "instances", "describe", self.vm_name,
             f"--zone={self.zone}", "--format=value(status)"]
        )
        if self.dry_run:
            return "RUNNING"
        return (result.stdout or "").strip() or "UNKNOWN"

    def ensure_running(self, wait_sec: int = 180) -> None:
        status = self.vm_status()
        print(f"[sdxl] VM {self.vm_name} status={status}")
        if status == "RUNNING":
            return
        print(f"[sdxl] VM を起動します (zone={self.zone}, スポット課金開始)...")
        start = self._run(
            ["compute", "instances", "start", self.vm_name, f"--zone={self.zone}"],
            timeout=wait_sec + 120,
        )
        if not self.dry_run and start.returncode != 0:
            raise RuntimeError(
                f"VM 起動に失敗しました (スポット在庫切れの可能性): {start.stderr.strip()[:300]}"
            )
        self._started_by_us = True
        if self.dry_run:
            return
        deadline = time.time() + wait_sec
        while time.time() < deadline:
            if self.vm_status() == "RUNNING":
                time.sleep(20)  # sshd 起動待ち
                return
            time.sleep(10)
        raise RuntimeError(f"VM が {wait_sec} 秒以内に RUNNING になりませんでした")

    def stop(self) -> None:
        print(f"[sdxl] VM {self.vm_name} を停止します (課金停止)...")
        result = self._run(
            ["compute", "instances", "stop", self.vm_name, f"--zone={self.zone}"],
            timeout=300,
        )
        if not self.dry_run and result.returncode != 0:
            print(
                "[WARN] VM の自動停止に失敗しました。手動で停止してください: "
                f"gcloud compute instances stop {self.vm_name} --zone={self.zone}\n"
                f"        {result.stderr.strip()[:200]}"
            )

    # ── inference ──────────────────────────────

    def generate(
        self,
        prompt: str,
        negative: str,
        out_dir: Path,
        count: int = 3,
        seed: int | None = None,
        keep_vm: bool = False,
    ) -> list[Path]:
        """VM 上で SDXL+LoRA 推論を実行し、生成画像を out_dir に回収して返す。"""
        if not self.base_model or not self.lora_path:
            if self.dry_run:
                print(
                    "[sdxl:dry-run] SDXL_REMOTE_BASE_MODEL / SDXL_REMOTE_LORA 未設定のため "
                    "プレースホルダで続行します (本番実行前に .env へ設定必須)。"
                )
                self.base_model = self.base_model or "<SDXL_REMOTE_BASE_MODEL>"
                self.lora_path = self.lora_path or "<SDXL_REMOTE_LORA>"
            else:
                raise RuntimeError(
                    ".env に SDXL_REMOTE_BASE_MODEL / SDXL_REMOTE_LORA を設定してください "
                    "(VM 上の絶対パス)。docs/setup.md 参照。"
                )

        params = {
            "prompt": prompt,
            "negative": negative,
            "count": count,
            "seed": seed,
            "base_model": self.base_model,
            "lora": self.lora_path,
            "lora_scale": self.lora_scale,
            "out": f"{self.workdir}/out",
        }
        local_script = Path(__file__).resolve().parents[2] / "scripts" / "sdxl_vm" / "infer_sdxl_lora.py"
        params_file = out_dir / "sdxl_params.json"
        params_file.write_text(json.dumps(params, ensure_ascii=False, indent=2), encoding="utf-8")

        try:
            self.ensure_running()

            print("[sdxl] スクリプト・パラメータを VM へ転送中...")
            self._ssh(f"mkdir -p {self.workdir}/out && rm -f {self.workdir}/out/*.png", timeout=120)
            for src in (local_script, params_file):
                result = self._scp(str(src), f"{self.vm_name}:{self.workdir}/")
                if not self.dry_run and result.returncode != 0:
                    raise RuntimeError(f"scp 失敗: {src.name} — {result.stderr.strip()[:300]}")

            print(f"[sdxl] 推論実行中 (count={count}, lora_scale={self.lora_scale})...")
            run = self._ssh(
                f"cd {self.workdir} && {self.remote_python} infer_sdxl_lora.py --params sdxl_params.json",
                timeout=1800,
            )
            if not self.dry_run and run.returncode != 0:
                raise RuntimeError(f"リモート推論に失敗: {(run.stderr or run.stdout).strip()[:500]}")

            print("[sdxl] 生成画像を回収中...")
            fetch = self._scp(f"{self.vm_name}:{self.workdir}/out/*.png", str(out_dir))
            if not self.dry_run and fetch.returncode != 0:
                raise RuntimeError(f"結果回収に失敗: {fetch.stderr.strip()[:300]}")

            images = sorted(out_dir.glob("*.png"))
            print(f"[sdxl] 回収完了: {len(images)} 枚")
            return images
        finally:
            if keep_vm:
                print("[sdxl] --keep-vm 指定のため VM は起動したままです (課金継続に注意)。")
            elif self._started_by_us or not self.dry_run:
                self.stop()


__all__ = ["SdxlVmClient"]
