from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TraceEvent:
    kind: str
    message: str
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentRunTrace:
    run_id: str
    task_id: str
    success: bool
    source: str
    events: list[TraceEvent]
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class PlaybookRule:
    id: str
    text: str
    version: int
    status: str  # candidate | promoted | rolled_back
    pass_rate_before: float | None
    pass_rate_after: float | None
    simulated: bool
    created_at: str
    parent_version: int | None = None
