"""Adapter for Claude Code CLI (`claude`)."""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path

from harness.agents.base import AgentResult


class ClaudeAdapter:
    name = "claude"

    def __init__(self, binary: str = "claude", model: str | None = None):
        self.binary = binary
        self.model = model

    def run(self, prompt: str, workdir: Path, timeout_s: int = 1800) -> AgentResult:
        if shutil.which(self.binary) is None:
            return AgentResult(ok=False, text=f"{self.binary} not found on PATH")
        cmd = [self.binary, "-p", prompt, "--output-format", "json"]
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
        text = self._extract(proc.stdout) or raw.strip()
        return AgentResult(ok=proc.returncode == 0, text=text, raw_log=raw,
                           elapsed_s=elapsed)

    @staticmethod
    def _extract(stdout: str) -> str:
        try:
            data = json.loads(stdout)
        except (json.JSONDecodeError, ValueError):
            return ""
        if isinstance(data, dict):
            return str(data.get("result", "") or "")
        return ""
