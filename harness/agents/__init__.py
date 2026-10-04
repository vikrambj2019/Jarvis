"""Agent adapter registry."""

from harness.agents.base import AgentAdapter, AgentResult
from harness.agents.claude import ClaudeAdapter
from harness.agents.codex import CodexAdapter
from harness.agents.mock import MockAdapter

ADAPTERS: dict[str, type[AgentAdapter]] = {
    "claude": ClaudeAdapter,
    "codex": CodexAdapter,
    "mock": MockAdapter,
}


def get_adapter(name: str, **kwargs) -> AgentAdapter:
    try:
        cls = ADAPTERS[name]
    except KeyError:
        raise ValueError(
            f"unknown agent {name!r}; choose from {sorted(ADAPTERS)}"
        ) from None
    return cls(**kwargs)  # type: ignore[call-arg]


__all__ = ["ADAPTERS", "AgentAdapter", "AgentResult", "get_adapter"]
