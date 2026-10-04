"""Uniform interface for specialist agent CLIs.

Each adapter shells out to one agent CLI and returns its result as text.
Adapters are deliberately thin: the harness owns memory, git, and sessions;
the agent owns the work.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass
class AgentResult:
    ok: bool
    text: str            # agent's output (transcript tail / result)
    raw_log: str = ""    # full captured stdout for the transcript file
    elapsed_s: float = 0.0


class AgentAdapter(Protocol):
    """One specialist agent behind a uniform call."""

    name: str

    def run(self, prompt: str, workdir: Path, timeout_s: int = 1800) -> AgentResult:
        """Run the agent non-interactively in workdir; capture everything."""
        ...
