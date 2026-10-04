# JARVIS — multi-agent harness

One orchestrator, many specialists. **Muse is the main** — this is the
on-machine counterpart that dispatches work to Claude Code and Codex CLIs with
**shared memory, session continuity, and git-worktree isolation**, across as
many projects as you like.

Talk to Muse about *what* to do; the harness handles *who does it, where, and
what they remember*.

## Install

On the machine where your agent CLIs live (`claude`, `codex` on PATH):

```bash
git clone <this-repo> && cd harness
pip install -e ".[dev]"   # dev extras are just pytest
```

`harness` (alias `jarvis`) is now on PATH. State lives in `~/.harness`
(override with `HARNESS_HOME`).

## The 2-minute tour

```bash
# Register your projects once
harness project add assay ~/workspace/assay
harness project add stars ~/workspace/stars-agentic

# Save durable facts every agent will see
harness remember "assay: pre-PR browser testing agent; never push to main directly"

# Dispatch work — Muse picks the agent, or you do
harness run --agent claude --project assay --task "fix the flaky stall-detector test"
harness run --agent codex  --project stars --task "add a measure-forecast CSV example" --background

# Watch the background crew
harness ps
harness log --session 20261004-051956-triage-the-open-pr-checklist

# Sessions keep continuity: later runs see earlier summaries
harness run --agent claude --project assay --session 20261004-051956-triage-the-open-pr-checklist \
  --task "now address the reviewer's second comment"
```

Each run: builds a briefing (memory + project notes + git state + session
history) → runs the agent in an **isolated git worktree** → saves the
transcript → appends the agent's `## Summary` to the session log. Worktrees are
kept after the run so you can review and merge deliberately.

## How Muse (main) uses it

From chat, Muse acts as strategist: it breaks work down, picks the agent per
task, and gives you the exact commands — or the task text to paste. `harness
brief` prints everything Muse needs to dispatch well:

```bash
harness brief --session <id>   # memory + session history + projects + agents
```

Memory discipline: agents **read** memory every run and **propose** additions in
their summaries; promotion to `MEMORY.md` is explicit via `harness remember`,
curated by Muse. Stored memory is injected as data, never as instructions.

## Commands

| Command | Purpose |
|---|---|
| `run --agent --task [--project] [--session] [--background] [--no-isolate] [--timeout] [--model]` | Dispatch a task |
| `remember "fact"` | Save to shared `MEMORY.md` |
| `recall [query]` | Read shared memory |
| `session list` / `session show <id>` | Inspect sessions |
| `project add <name> <path>` / `remove` / `list` | Register projects |
| `ps [--session]` / `log --session` | Background runs |
| `brief [--session]` | Context dump for the main orchestrator |

Agents: `claude` (Claude Code CLI), `codex` (Codex CLI), `mock` (dry-run/testing).
New agents are ~30 lines: subclass the adapter protocol in `harness/agents/`.

## Design notes

- **Thin adapters, fat harness.** The harness owns memory, git, and sessions;
  the agent owns the work. Swapping a model never touches orchestration.
- **Isolation by default.** Git worktrees per task; `--no-isolate` to work in place.
- **Sessions are the memory unit.** A session spans many runs across agents and
  projects; each run sees what earlier runs concluded.
- **Background-first for parallel work.** Multiple agents on multiple projects
  at once is the normal mode, not the exception.

## Testing

```bash
python -m pytest tests/ -q
```

Tests use the mock adapter — no API keys, no CLIs, no network.
