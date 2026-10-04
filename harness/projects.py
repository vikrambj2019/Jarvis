"""Project registry + git worktree isolation.

Projects are registered once (`harness project add <name> <path>`) and then
addressed by name. Each isolated run gets its own git worktree so parallel
agents never step on each other's files.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from harness.config import ensure_home, projects_path, worktrees_dir


def load_projects(home: Path | None = None) -> dict:
    ensure_home(home)
    try:
        return json.loads(projects_path(home).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_projects(projects: dict, home: Path | None = None) -> None:
    projects_path(home).write_text(json.dumps(projects, indent=2) + "\n",
                                   encoding="utf-8")


def add_project(name: str, path: str, home: Path | None = None) -> Path:
    """Register a project; returns its resolved path."""
    p = Path(path).expanduser().resolve()
    if not p.is_dir():
        raise ValueError(f"project path does not exist: {p}")
    projects = load_projects(home)
    projects[name] = {"path": str(p)}
    save_projects(projects, home)
    return p


def remove_project(name: str, home: Path | None = None) -> None:
    projects = load_projects(home)
    if name not in projects:
        raise ValueError(f"unknown project {name!r}")
    del projects[name]
    save_projects(projects, home)


def project_path(name: str, home: Path | None = None) -> Path:
    projects = load_projects(home)
    try:
        return Path(projects[name]["path"])
    except KeyError:
        raise ValueError(
            f"unknown project {name!r}; registered: {sorted(projects) or 'none'}"
        ) from None


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:40] or "task"


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def is_git_repo(path: Path) -> bool:
    return _git(["rev-parse", "--git-dir"], path).returncode == 0


def make_worktree(repo: Path, session_id: str, task: str,
                  home: Path | None = None) -> Path:
    """Create an isolated worktree for one task run. Returns its path."""
    if not is_git_repo(repo):
        raise ValueError(f"not a git repo: {repo}")
    # Base the worktree on the repo's current HEAD branch.
    branch_probe = _git(["branch", "--show-current"], repo)
    base = branch_probe.stdout.strip() or "HEAD"
    wt = worktrees_dir(home) / session_id / _slug(task)
    wt.parent.mkdir(parents=True, exist_ok=True)
    branch = f"harness/{session_id}/{_slug(task)}"
    proc = _git(["worktree", "add", "-b", branch, str(wt), base], repo)
    if proc.returncode != 0:
        raise RuntimeError(f"git worktree add failed: {proc.stderr.strip()}")
    return wt


def remove_worktree(repo: Path, wt: Path) -> None:
    """Remove a worktree created by make_worktree (keeps the branch)."""
    proc = _git(["worktree", "remove", "--force", str(wt)], repo)
    if proc.returncode != 0:
        raise RuntimeError(f"git worktree remove failed: {proc.stderr.strip()}")


def git_status_summary(repo: Path, max_lines: int = 30) -> str:
    """Compact git status + recent log for briefing injection."""
    if not is_git_repo(repo):
        return "(not a git repo)"
    status = _git(["status", "--short"], repo).stdout.strip()
    log = _git(["log", "--oneline", "-5"], repo).stdout.strip()
    branch = _git(["branch", "--show-current"], repo).stdout.strip()
    lines = [f"branch: {branch or '(detached)'}"]
    if log:
        lines.append("recent commits:\n" + log)
    if status:
        lines.append("working tree:\n" + "\n".join(status.splitlines()[:max_lines]))
    else:
        lines.append("working tree: clean")
    return "\n".join(lines)
