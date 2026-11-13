from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

from .models import AgentRunTrace, TraceEvent


def _events_from_generic(obj: dict[str, Any]) -> list[TraceEvent]:
    raw_events = obj.get("events") or []
    out: list[TraceEvent] = []
    for e in raw_events:
        if isinstance(e, dict):
            out.append(
                TraceEvent(
                    kind=str(e.get("kind", "log")),
                    message=str(e.get("message", "")),
                    meta={k: v for k, v in e.items() if k not in ("kind", "message")},
                )
            )
        else:
            out.append(TraceEvent(kind="log", message=str(e)))
    return out


def parse_generic_line(line: dict[str, Any]) -> AgentRunTrace:
    return AgentRunTrace(
        run_id=str(line.get("run_id", "unknown")),
        task_id=str(line.get("task_id", "unknown")),
        success=bool(line.get("success")),
        source=str(line.get("source", "generic")),
        events=_events_from_generic(line),
        raw=line,
    )


def parse_claude_code_line(line: dict[str, Any]) -> AgentRunTrace:
    """Adapter for Claude Code-style session exports."""
    task_id = str(line.get("cwd_task") or line.get("task_id") or "unknown")
    run_id = str(line.get("session_id") or line.get("run_id") or "claude-session")
    messages = line.get("messages") or line.get("transcript") or []
    events: list[TraceEvent] = []
    for m in messages:
        if not isinstance(m, dict):
            continue
        role = m.get("role", "assistant")
        content = m.get("content", "")
        if isinstance(content, list):
            text = " ".join(
                str(c.get("text", c)) if isinstance(c, dict) else str(c) for c in content
            )
        else:
            text = str(content)
        events.append(TraceEvent(kind=role, message=text[:2000], meta={"tool": m.get("tool")}))
    success = line.get("success")
    if success is None:
        success = any("tests passed" in e.message.lower() for e in events)
    return AgentRunTrace(
        run_id=run_id,
        task_id=task_id,
        success=bool(success),
        source="claude_code",
        events=events,
        raw=line,
    )


def parse_openhands_line(line: dict[str, Any]) -> AgentRunTrace:
    """Adapter for OpenHands-style event logs."""
    task_id = str(line.get("task_name") or line.get("task_id") or "unknown")
    run_id = str(line.get("instance_id") or line.get("run_id") or "openhands-run")
    actions = line.get("actions") or line.get("history") or []
    events: list[TraceEvent] = []
    for a in actions:
        if not isinstance(a, dict):
            events.append(TraceEvent(kind="action", message=str(a)))
            continue
        atype = str(a.get("type") or a.get("action") or "action")
        msg = str(a.get("message") or a.get("thought") or a.get("content") or atype)
        events.append(TraceEvent(kind=atype, message=msg[:2000], meta=a))
    err = line.get("error") or line.get("exit_status")
    success = line.get("success")
    if success is None:
        success = err in (None, 0, "success")
    return AgentRunTrace(
        run_id=run_id,
        task_id=task_id,
        success=bool(success),
        source="openhands",
        events=events,
        raw=line,
    )


ADAPTERS = {
    "generic": parse_generic_line,
    "claude_code": parse_claude_code_line,
    "openhands": parse_openhands_line,
}


def iter_traces(path: Path, adapter: str = "auto") -> Iterator[AgentRunTrace]:
    with path.open(encoding="utf-8") as f:
        for lineno, raw in enumerate(f, 1):
            raw = raw.strip()
            if not raw:
                continue
            line = json.loads(raw)
            fmt = adapter
            if fmt == "auto":
                fmt = str(line.get("format") or line.get("source") or "generic")
                if fmt not in ADAPTERS:
                    if "messages" in line or "session_id" in line:
                        fmt = "claude_code"
                    elif "actions" in line or "instance_id" in line:
                        fmt = "openhands"
                    else:
                        fmt = "generic"
            parser = ADAPTERS.get(fmt, parse_generic_line)
            try:
                yield parser(line)
            except Exception as exc:  # noqa: BLE001 — surface bad lines in ingest stats
                yield AgentRunTrace(
                    run_id=f"parse-error-{lineno}",
                    task_id="unknown",
                    success=False,
                    source=fmt,
                    events=[TraceEvent(kind="error", message=str(exc))],
                    raw=line,
                )


def ingest_jsonl(path: Path, adapter: str = "auto") -> list[AgentRunTrace]:
    return list(iter_traces(path, adapter=adapter))
