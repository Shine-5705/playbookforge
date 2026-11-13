from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

from .models import AgentRunTrace, PlaybookRule
from .store import PlaybookStore, _utc_now

FAILURE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"edit.*config|changed.*\.env|modified.*yaml", re.I), "Run the task test suite before editing config or environment files."),
    (re.compile(r"skip.*test|without.*test", re.I), "Always run tests after every code change, even for small edits."),
    (re.compile(r"delete.*test|removed.*test", re.I), "Never delete or disable failing tests; fix the implementation instead."),
    (re.compile(r"pip install|npm install", re.I), "Verify dependency changes against the task's pinned requirements before installing packages."),
    (re.compile(r"assert.*fail|AssertionError", re.I), "Read the assertion message and reproduce the failing case locally before patching."),
    (re.compile(r"timeout|timed out", re.I), "If a command hangs, reduce scope and run the smallest failing test in isolation."),
    (re.compile(r"lint|eslint|ruff", re.I), "Run linters only after unit tests pass to avoid fixing style on broken code."),
    (re.compile(r"git reset|revert", re.I), "Before reverting, capture which edit introduced the regression with a minimal diff."),
]


def _trace_blob(trace: AgentRunTrace) -> str:
    parts = [f"task={trace.task_id}", f"success={trace.success}"]
    for e in trace.events[-20:]:
        parts.append(f"{e.kind}:{e.message[:200]}")
    return "\n".join(parts)


def demo_rules_from_traces(failed: list[AgentRunTrace]) -> list[str]:
    """Deterministic DEMO_MODE rule extraction."""
    seen: set[str] = set()
    rules: list[str] = []
    for trace in failed:
        blob = _trace_blob(trace)
        for pattern, rule in FAILURE_PATTERNS:
            if pattern.search(blob) and rule not in seen:
                seen.add(rule)
                rules.append(rule)
        if not trace.success and len(rules) < 3:
            fallback = (
                f"For task `{trace.task_id}`, read failing test output first, then change one file at a time."
            )
            if fallback not in seen:
                seen.add(fallback)
                rules.append(fallback)
    if not rules:
        rules.append("Run tests before editing config files.")
    return rules[:5]


def _openai_chat(prompt: str, api_key: str) -> str:
    body = json.dumps(
        {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": "Extract concise playbook rules (imperative sentences) from failed agent traces. Return JSON: {\"rules\": [\"...\"]}.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
    ).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode())
    return data["choices"][0]["message"]["content"]


def _anthropic_chat(prompt: str, api_key: str) -> str:
    body = json.dumps(
        {
            "model": "claude-3-5-haiku-20241022",
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
            "system": "Extract concise playbook rules from failed agent traces. Return JSON: {\"rules\": [\"...\"]}.",
        }
    ).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode())
    return data["content"][0]["text"]


def _parse_rules_json(text: str) -> list[str]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```\w*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    try:
        obj = json.loads(text)
        rules = obj.get("rules") or obj.get("playbook_rules") or []
        return [str(r) for r in rules if r]
    except json.JSONDecodeError:
        return [line.strip("- ").strip() for line in text.splitlines() if line.strip()][:5]


def llm_distill_rules(traces: list[AgentRunTrace]) -> tuple[list[str], bool]:
    """Returns (rules, simulated). simulated=True when DEMO_MODE or no API key."""
    failed = [t for t in traces if not t.success]
    demo_mode = os.environ.get("DEMO_MODE", "").lower() in ("1", "true", "yes")
    if demo_mode:
        return demo_rules_from_traces(failed), True

    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not openai_key and not anthropic_key:
        return demo_rules_from_traces(failed), True

    prompt = "Failed agent traces:\n\n" + "\n---\n".join(_trace_blob(t) for t in failed[:15])
    try:
        if openai_key:
            raw = _openai_chat(prompt, openai_key)
        else:
            raw = _anthropic_chat(prompt, anthropic_key)
        rules = _parse_rules_json(raw)
        if rules:
            return rules[:5], False
    except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError):
        pass
    return demo_rules_from_traces(failed), True


def stable_rule_id(rule_text: str) -> str:
    h = hashlib.sha256(rule_text.encode()).hexdigest()[:8]
    return f"rule-{h}"


def persist_candidates(
    store: PlaybookStore, rule_texts: list[str], simulated: bool
) -> list[PlaybookRule]:
    created: list[PlaybookRule] = []
    for text in rule_texts:
        rid = stable_rule_id(text)
        existing = store.get_rule(rid)
        version = 1 if not existing else existing.version
        if existing and existing.text == text and existing.status == "candidate":
            created.append(existing)
            continue
        if existing:
            version = existing.version
        rule = PlaybookRule(
            id=rid,
            text=text,
            version=version if not existing else version + 1,
            status="candidate",
            pass_rate_before=None,
            pass_rate_after=None,
            simulated=simulated,
            created_at=_utc_now(),
            parent_version=existing.version if existing else None,
        )
        store.insert_rule(rule)
        created.append(rule)
    return created
