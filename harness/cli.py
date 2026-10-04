"""harness / jarvis — JARVIS-style multi-agent orchestrator CLI.

Muse is the main. This CLI is the on-machine counterpart: it dispatches work
to specialist agent CLIs (Claude Code, Codex) with shared memory, session
continuity, and git-worktree isolation.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from harness import memory as mem
from harness.agents import ADAPTERS
from harness.config import HARNESS_HOME, ensure_home
from harness.projects import (
    add_project,
    load_projects,
    project_path,
    remove_project,
)
from harness.runner import (
    RunSpec,
    refresh_runs,
    run_task,
    run_task_background,
)


def _home() -> Path:
    return ensure_home(HARNESS_HOME)


# ── run ───────────────────────────────────────────────────────────────────

def _cmd_run(args) -> int:
    home = _home()
    spec = RunSpec(
        agent=args.agent,
        project=args.project,
        task=args.task,
        session_id=args.session,
        isolate=not args.no_isolate,
        timeout_s=args.timeout,
        model=args.model,
        background=args.background,
        workdir=Path(args.workdir).expanduser() if args.workdir else None,
    )
    if args.background:
        run_task_background(spec, home)
        return 0
    record = run_task(spec, home)
    print(f"\n## {spec.agent} summary\n{record['summary']}")
    return 0 if record["ok"] else 1


# ── memory ────────────────────────────────────────────────────────────────

def _cmd_remember(args) -> int:
    home = _home()
    mem.remember(args.text, home)
    print(f"remembered → {home / 'MEMORY.md'}")
    return 0


def _cmd_recall(args) -> int:
    print(mem.recall(args.query or "", _home()))
    return 0


# ── sessions ──────────────────────────────────────────────────────────────

def _cmd_session(args) -> int:
    home = _home()
    if args.action == "list":
        sessions = mem.list_sessions(home)
        if not sessions:
            print("(no sessions yet)")
        for s in sessions:
            print(s.name)
    elif args.action == "show":
        sdir = home / "sessions" / args.id
        if not sdir.is_dir():
            print(f"unknown session {args.id!r}", file=sys.stderr)
            return 1
        print(f"== {args.id} ==")
        print((sdir / "summaries.md").read_text(encoding="utf-8"))
    return 0


# ── projects ──────────────────────────────────────────────────────────────

def _cmd_project(args) -> int:
    home = _home()
    if args.action == "add":
        p = add_project(args.name, args.path, home)
        print(f"project {args.name!r} → {p}")
    elif args.action == "remove":
        remove_project(args.name, home)
        print(f"removed project {args.name!r}")
    elif args.action == "list":
        projects = load_projects(home)
        if not projects:
            print("(no projects registered)")
        for name, info in projects.items():
            print(f"{name}: {info['path']}")
    return 0


# ── background runs ───────────────────────────────────────────────────────

def _cmd_ps(args) -> int:
    home = _home()
    sessions = [home / "sessions" / args.session] if args.session else mem.list_sessions(home)
    found = False
    for sdir in sessions:
        if not sdir.is_dir():
            continue
        for r in refresh_runs(sdir):
            found = True
            state = "done" if r["done"] else f"running (pid {r['pid']})"
            print(f"{sdir.name} | {r['agent']} | {r['task'][:50]} | {state}")
    if not found:
        print("(no background runs)")
    return 0


def _cmd_log(args) -> int:
    home = _home()
    sdir = home / "sessions" / args.session
    if not sdir.is_dir():
        print(f"unknown session {args.session!r}", file=sys.stderr)
        return 1
    runs = refresh_runs(sdir)
    if not runs:
        print("(no background runs in this session)")
        return 0
    log = Path(runs[-1]["log"])
    lines = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    print("\n".join(lines[-args.tail:]))
    return 0


# ── brief: context for the main orchestrator ──────────────────────────────

def _cmd_brief(args) -> int:
    """Print everything Muse (main) needs to dispatch: memory + session state."""
    home = _home()
    print("# Harness memory\n")
    print(mem.read_memory(home))
    if args.session:
        sdir = home / "sessions" / args.session
        if sdir.is_dir():
            print(f"\n# Session {args.session}\n")
            print(mem.session_context(sdir, max_chars=12000))
    else:
        print("\n# Recent sessions")
        for s in mem.list_sessions(home)[:5]:
            print(f"- {s.name}")
    print("\n# Projects")
    for name, info in load_projects(home).items():
        print(f"- {name}: {info['path']}")
    print(f"\n# Agents: {', '.join(sorted(ADAPTERS))}")
    return 0


# ── parser ────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="harness",
        description="JARVIS-style orchestrator: dispatch Claude/Codex agents "
                    "with shared memory, sessions, and git isolation. "
                    "Muse is the main.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    r = sub.add_parser("run", help="dispatch a task to an agent")
    r.add_argument("--agent", required=True, choices=sorted(ADAPTERS))
    r.add_argument("--task", required=True, help="the task in plain language")
    r.add_argument("--project", default=None, help="registered project name")
    r.add_argument("--workdir", default=None, help="explicit dir (overrides project)")
    r.add_argument("--session", default=None, help="existing session id (else new)")
    r.add_argument("--no-isolate", action="store_true",
                   help="skip git worktree isolation; work in place")
    r.add_argument("--background", action="store_true",
                   help="run detached; inspect with ps/log")
    r.add_argument("--timeout", type=int, default=1800)
    r.add_argument("--model", default=None, help="model override for the adapter")
    r.set_defaults(func=_cmd_run)

    m = sub.add_parser("remember", help="save a durable fact to shared memory")
    m.add_argument("text", help="the fact to remember")
    m.set_defaults(func=_cmd_remember)

    c = sub.add_parser("recall", help="read shared memory")
    c.add_argument("query", nargs="?", default="", help="optional filter")
    c.set_defaults(func=_cmd_recall)

    s = sub.add_parser("session", help="inspect sessions")
    s.add_argument("action", choices=["list", "show"])
    s.add_argument("id", nargs="?", default=None)
    s.set_defaults(func=_cmd_session)

    j = sub.add_parser("project", help="register projects")
    j.add_argument("action", choices=["add", "remove", "list"])
    j.add_argument("name", nargs="?", default=None)
    j.add_argument("path", nargs="?", default=None)
    j.set_defaults(func=_cmd_project)

    ps = sub.add_parser("ps", help="background agent runs")
    ps.add_argument("--session", default=None)
    ps.set_defaults(func=_cmd_ps)

    lg = sub.add_parser("log", help="tail a background run's log")
    lg.add_argument("--session", required=True)
    lg.add_argument("--tail", type=int, default=40)
    lg.set_defaults(func=_cmd_log)

    b = sub.add_parser("brief", help="print memory+session context for the main orchestrator")
    b.add_argument("--session", default=None)
    b.set_defaults(func=_cmd_brief)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except ValueError as exc:
        print(f"harness: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
