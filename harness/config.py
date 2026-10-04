"""Paths and home-directory bootstrap for the harness."""

from __future__ import annotations

import os
from pathlib import Path


def _home() -> Path:
    return Path(os.environ.get("HARNESS_HOME", Path.home() / ".harness"))


HARNESS_HOME: Path = _home()


def ensure_home(home: Path | None = None) -> Path:
    """Create the harness home layout if missing; return it."""
    h = home or HARNESS_HOME
    (h / "sessions").mkdir(parents=True, exist_ok=True)
    (h / "worktrees").mkdir(parents=True, exist_ok=True)
    mem = h / "MEMORY.md"
    if not mem.exists():
        mem.write_text(
            "# Harness memory\n\n"
            "Durable facts shared across all agents and sessions.\n"
            "Curated by the main orchestrator (Muse) via `harness remember`.\n"
            "Agents may propose additions in their summaries; promotion is explicit.\n",
            encoding="utf-8",
        )
    proj = h / "projects.json"
    if not proj.exists():
        proj.write_text("{}\n", encoding="utf-8")
    return h


def memory_path(home: Path | None = None) -> Path:
    return (home or HARNESS_HOME) / "MEMORY.md"


def projects_path(home: Path | None = None) -> Path:
    return (home or HARNESS_HOME) / "projects.json"


def sessions_dir(home: Path | None = None) -> Path:
    return (home or HARNESS_HOME) / "sessions"


def worktrees_dir(home: Path | None = None) -> Path:
    return (home or HARNESS_HOME) / "worktrees"
