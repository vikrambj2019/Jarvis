"""Tests for the harness. No real agent CLIs; the mock adapter stands in."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness import memory as mem
from harness.config import ensure_home
from harness.projects import add_project, load_projects, project_path, remove_project
from harness.runner import RunSpec, build_briefing, extract_summary, run_task


@pytest.fixture
def home(tmp_path: Path, monkeypatch) -> Path:
    h = tmp_path / "harness-home"
    monkeypatch.setenv("HARNESS_HOME", str(h))
    import harness.config as cfg
    monkeypatch.setattr(cfg, "HARNESS_HOME", h)
    ensure_home(h)
    return h


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "demo-repo"
    r.mkdir()
    (r / "README.md").write_text("# demo\n", encoding="utf-8")
    import subprocess
    subprocess.run(["git", "init", "-q"], cwd=r, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=r, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=r, check=True)
    subprocess.run(["git", "add", "."], cwd=r, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=r, check=True)
    return r


# ── memory ────────────────────────────────────────────────────────────────

def test_remember_and_recall(home: Path):
    mem.remember("assay repo lives at ~/workspace/assay", home)
    mem.remember("user prefers terse summaries", home)
    all_mem = mem.recall("", home)
    assert "assay repo" in all_mem
    assert "terse summaries" in all_mem
    filtered = mem.recall("assay", home)
    assert "assay repo" in filtered
    assert "terse summaries" not in filtered


def test_session_roundtrip(home: Path):
    sdir = mem.new_session("demo task", home)
    assert sdir.is_dir()
    mem.append_summary(sdir, "mock", "demo task", "## Summary\nDid it.")
    ctx = mem.session_context(sdir)
    assert "Did it." in ctx
    assert sdir.name in [p.name for p in mem.list_sessions(home)]


# ── projects ──────────────────────────────────────────────────────────────

def test_project_registry(home: Path, repo: Path):
    add_project("demo", str(repo), home)
    assert load_projects(home)["demo"]["path"] == str(repo)
    assert project_path("demo", home) == repo
    remove_project("demo", home)
    with pytest.raises(ValueError):
        project_path("demo", home)


# ── briefing + summary extraction ─────────────────────────────────────────

def test_briefing_injects_memory_and_task(home: Path, repo: Path):
    mem.remember("never push to main directly", home)
    sdir = mem.new_session("x", home)
    brief = build_briefing("fix the bug", repo, sdir, "demo", home)
    assert "never push to main directly" in brief
    assert "fix the bug" in brief
    assert "branch:" in brief  # git state included


def test_extract_summary():
    text = "did stuff\n## Summary\n- changed foo.py\n- tests pass\n"
    assert "changed foo.py" in extract_summary(text)


def test_extract_summary_fallback():
    s = extract_summary("no headings here\njust output")
    assert "just output" in s


# ── end-to-end run with mock agent ────────────────────────────────────────

def test_run_task_mock_agent(home: Path, repo: Path):
    add_project("demo", str(repo), home)
    spec = RunSpec(agent="mock", project="demo", task="add a hello file")
    record = run_task(spec, home)

    assert record["ok"] is True
    assert record["agent"] == "mock"
    assert record["worktree"] is not None  # isolated by default
    wt = Path(record["worktree"])
    assert (wt / "README.md").exists()  # worktree has repo contents

    session_dir = home / "sessions" / record["session"]
    assert (session_dir / "brief.md").exists()
    assert "add a hello file" in (session_dir / "brief.md").read_text()
    assert list(session_dir.glob("transcript-*.log"))
    summaries = (session_dir / "summaries.md").read_text()
    assert "add a hello file" in summaries


def test_run_task_no_isolate(home: Path, repo: Path):
    add_project("demo", str(repo), home)
    spec = RunSpec(agent="mock", project="demo", task="x", isolate=False)
    record = run_task(spec, home)
    assert record["worktree"] is None
    assert Path(record["workdir"]) == repo


def test_run_task_continues_session(home: Path, repo: Path):
    add_project("demo", str(repo), home)
    r1 = run_task(RunSpec(agent="mock", project="demo", task="first"), home)
    r2 = run_task(RunSpec(agent="mock", project="demo", task="second",
                          session_id=r1["session"]), home)
    assert r1["session"] == r2["session"]
    summaries = (home / "sessions" / r1["session"] / "summaries.md").read_text()
    assert "first" in summaries and "second" in summaries


def test_unknown_agent_rejected(home: Path):
    with pytest.raises(ValueError):
        run_task(RunSpec(agent="nope", project=None, task="x"), home)
