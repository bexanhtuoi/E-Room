from __future__ import annotations

from enum import Enum
from typing import Any

from app.agent.corrector import AgentCorrector
from app.agent.expert import AgentExpert
from app.agent.heartbeat import AgentHeartbeat
from app.log import get_logger

logger = get_logger(__name__)


class AgentNodeKind(str, Enum):
    CORRECTOR = "corrector"
    EXPERT = "expert"
    HEARTBEAT = "heartbeat"


class AgentNode:
    """A configured agent node ready to process input."""

    __slots__ = ("kind", "name", "agent")

    def __init__(self, kind: AgentNodeKind, name: str, agent: Any) -> None:
        self.kind = kind
        self.name = name
        self.agent = agent

    def to_dict(self) -> dict[str, str]:
        return {"kind": self.kind.value, "name": self.name, "status": "ready"}


_AGENT_CLASSES = {
    AgentNodeKind.CORRECTOR: AgentCorrector,
    AgentNodeKind.EXPERT: AgentExpert,
    AgentNodeKind.HEARTBEAT: AgentHeartbeat,
}


def create_agent_node(kind: AgentNodeKind | str, name: str = "") -> AgentNode:
    """Create and initialize an agent node of the given kind.

    Args:
        kind: One of "corrector", "expert", or "heartbeat" (or AgentNodeKind enum).
        name: Human-readable label for this node instance.

    Returns:
        An AgentNode wrapping a ready-to-use agent instance.
    """
    if isinstance(kind, str):
        kind = AgentNodeKind(kind)
    agent_cls = _AGENT_CLASSES[kind]
    agent = agent_cls()
    node = AgentNode(kind=kind, name=name or kind.value, agent=agent)
    logger.info("agent_node_created", extra={"kind": kind.value, "name": node.name})
    return node


def create_all_nodes() -> dict[AgentNodeKind, AgentNode]:
    """Create all three agent nodes at once.

    Returns:
        Dict mapping each AgentNodeKind to its AgentNode.
    """
    return {k: create_agent_node(kind=k) for k in AgentNodeKind}
