"""Mock adapter for tests, dry runs, and demos. No CLI required."""

from __future__ import annotations

import time
from pathlib import Path

from harness.agents.base import AgentResult


class MockAdapter:
    """Pretends to do the task: lists the workdir top level and returns a
    canned summary. Used by tests and `harness run --agent mock`."""

    name = "mock"

    def __init__(self, summary: str = "Did the thing.\n## Summary\nDone (mock)."):
        self.summary = summary
        self.last_prompt: str = ""
        self.last_workdir: Path | None = None

    def run(self, prompt: str, workdir: Path, timeout_s: int = 1800) -> AgentResult:
        start = time.monotonic()
        self.last_prompt = prompt
        self.last_workdir = workdir
        try:
            listing = ", ".join(sorted(p.name for p in workdir.iterdir())[:10])
        except OSError:
            listing = "(unreadable)"
        text = f"Working in {workdir} (top: {listing}).\n{self.summary}"
        return AgentResult(ok=True, text=text, raw_log=text,
                           elapsed_s=time.monotonic() - start)
