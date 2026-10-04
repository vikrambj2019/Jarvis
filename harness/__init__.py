"""JARVIS-style agent harness.

Muse is the main orchestrator. This package is the on-machine counterpart:
it dispatches work to specialist agent CLIs (Claude Code, Codex), gives them
shared memory and session continuity, and isolates their work in git worktrees.

Layout of HARNESS_HOME (default ~/.harness, override with HARNESS_HOME):
    MEMORY.md            durable cross-session memory (curated)
    projects.json        registered projects: name -> {path, notes}
    sessions/<id>/      one dir per session:
        brief.md         the briefing injected into the agent
        transcript.log   raw agent output
        summary.md       agent's trailing summary + runner metadata
        runs.json        background run records
    worktrees/<s>/<t>/  git worktrees, one per isolated task run
"""

from harness.config import HARNESS_HOME, ensure_home

__all__ = ["HARNESS_HOME", "ensure_home"]
__version__ = "0.1.0"
