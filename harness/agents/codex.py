"""Adapter for OpenAI Codex CLI (`codex`)."""

from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

from harness.agents.base import AgentResult


class CodexAdapter:
    name = "codex"

    def __init__(self, binary: str = "codex", model: str | None = None,
                 sandbox: str = "workspace-write"):
        self.binary = binary
        self.model = model
        self.sandbox = sandbox

    def run(self, prompt: str, workdir: Path, timeout_s: int = 1800) -> AgentResult:
        if shutil.which(self.binary) is None:
            return AgentResult(ok=False, text=f"{self.binary} not found on PATH")
        cmd = [self.binary, "exec", "--sandbox", self.sandbox, prompt]
        if self.model:
            cmd += ["--model", self.model]
        start = time.monotonic()
        try:
            proc = subprocess.run(
                cmd, cwd=workdir, capture_output=True, text=True, timeout=timeout_s
            )
        except subprocess.TimeoutExpired:
            return AgentResult(ok=False, text=f"timed out after {timeout_s}s",
                               elapsed_s=time.monotonic() - start)
        elapsed = time.monotonic() - start
        raw = proc.stdout + proc.stderr
        return AgentResult(ok=proc.returncode == 0,
                           text=proc.stdout.strip() or raw.strip(),
                           raw_log=raw, elapsed_s=elapsed)
