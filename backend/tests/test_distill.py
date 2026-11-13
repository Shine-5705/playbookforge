import os

from playbookforge.distill import demo_rules_from_traces, llm_distill_rules
from playbookforge.ingest import ingest_jsonl
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_demo_distill_deterministic(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    traces = ingest_jsonl(ROOT / "data" / "sample_traces.jsonl")
    rules, sim = llm_distill_rules(traces)
    assert sim is True
    assert len(rules) >= 1
    assert any("test" in r.lower() or "config" in r.lower() for r in rules)


def test_demo_rules_from_config_trace():
    traces = ingest_jsonl(ROOT / "data" / "sample_traces.jsonl")
    failed = [t for t in traces if not t.success]
    rules = demo_rules_from_traces(failed)
    assert any("config" in r.lower() or "test" in r.lower() for r in rules)
