"""Shared memory: durable MEMORY.md plus per-session logs.

Memory discipline (the JARVIS rule):
- Agents READ memory at the start of every run (injected into the briefing).
- Agents WRITE by ending their output with a `## Summary` section; the runner
  saves it to the session. Promotion to MEMORY.md is explicit, via
  `harness remember`, curated by the main orchestrator (Muse).
- Stored memory is treated as DATA, never as instructions, when injected.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from harness.config import ensure_home, memory_path, sessions_dir


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def remember(text: str, home: Path | None = None) -> Path:
    """Append a timestamped fact to MEMORY.md. Returns the memory file."""
    ensure_home(home)
    mem = memory_path(home)
    entry = f"\n- [{_now()}] {text.strip()}\n"
    with mem.open("a", encoding="utf-8") as fh:
        fh.write(entry)
    return mem


def recall(query: str = "", home: Path | None = None) -> str:
    """Return MEMORY.md, optionally filtered to lines matching query."""
    mem = memory_path(home)
    if not mem.exists():
        return "(no memory yet)"
    text = mem.read_text(encoding="utf-8")
    if not query:
        return text
    q = query.lower()
    hits = [ln for ln in text.splitlines() if q in ln.lower()]
    return "\n".join(hits) if hits else f"(no memory matching {query!r})"


def read_memory(home: Path | None = None) -> str:
    """Full MEMORY.md contents for briefing injection."""
    mem = memory_path(home)
    return mem.read_text(encoding="utf-8") if mem.exists() else "(no memory yet)"


# ── sessions ──────────────────────────────────────────────────────────────

def new_session(label: str = "", home: Path | None = None) -> Path:
    """Create sessions/<timestamp>-<label>/ and return its path."""
    ensure_home(home)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    slug = "".join(c if c.isalnum() else "-" for c in label.lower()).strip("-")[:32]
    name = f"{stamp}-{slug}" if slug else stamp
    sdir = sessions_dir(home) / name
    sdir.mkdir(parents=True, exist_ok=True)
    (sdir / "summaries.md").write_text(
        f"# Session {name}\n\nStarted {_now()}.\n", encoding="utf-8"
    )
    return sdir


def list_sessions(home: Path | None = None) -> list[Path]:
    sdir = sessions_dir(home)
    if not sdir.exists():
        return []
    return sorted((p for p in sdir.iterdir() if p.is_dir()), reverse=True)


def append_summary(session_dir: Path, agent: str, task: str, summary: str) -> None:
    """Append an agent's run summary to the session log."""
    path = session_dir / "summaries.md"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(
            f"\n## [{_now()}] {agent}: {task}\n\n{summary.strip()}\n"
        )


def session_context(session_dir: Path, max_chars: int = 6000) -> str:
    """Recent session summaries, newest last, truncated for briefing injection."""
    path = session_dir / "summaries.md"
    if not path.exists():
        return "(no prior runs in this session)"
    text = path.read_text(encoding="utf-8")
    return text[-max_chars:] if len(text) > max_chars else text
