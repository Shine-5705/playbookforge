from pathlib import Path

from playbookforge.ingest import ingest_jsonl, parse_claude_code_line, parse_generic_line

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "data" / "sample_traces.jsonl"


def test_ingest_sample_file():
    traces = ingest_jsonl(SAMPLE)
    assert len(traces) >= 4
    assert any(t.source == "claude_code" for t in traces)
    assert any(not t.success for t in traces)


def test_generic_line():
    line = {"run_id": "r", "task_id": "t", "success": False, "events": [{"kind": "x", "message": "y"}]}
    t = parse_generic_line(line)
    assert t.run_id == "r" and not t.success


def test_claude_adapter():
    line = {"session_id": "s", "messages": [{"role": "assistant", "content": "hello"}], "success": False}
    t = parse_claude_code_line(line)
    assert t.source == "claude_code"
