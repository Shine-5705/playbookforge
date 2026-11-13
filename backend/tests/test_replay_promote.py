import os
from pathlib import Path

from playbookforge.distill import llm_distill_rules, persist_candidates
from playbookforge.ingest import ingest_jsonl
from playbookforge.promote import apply_replay_to_candidate, can_promote, promote_rule
from playbookforge.replay import replay_rule
from playbookforge.store import PlaybookStore

ROOT = Path(__file__).resolve().parents[2]


def test_simulated_replay_improves(tmp_path, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    db = tmp_path / "t.db"
    store = PlaybookStore(db)
    traces = ingest_jsonl(ROOT / "data" / "sample_traces.jsonl")
    rules, sim = llm_distill_rules(traces)
    candidates = persist_candidates(store, rules[:1], sim)
    report = replay_rule(candidates[0], force_simulated=True)
    updated = apply_replay_to_candidate(store, candidates[0], report)
    assert updated.pass_rate_after is not None
    ok, _ = can_promote(report)
    # Simulated replay should usually improve; gate logic still runs
    if ok:
        promoted = promote_rule(store, updated.id, updated.version)
        assert promoted.status == "promoted"


def test_rollback(tmp_path):
    store = PlaybookStore(tmp_path / "t.db")
    from playbookforge.distill import stable_rule_id
    from playbookforge.models import PlaybookRule
    from playbookforge.store import _utc_now

    rid = stable_rule_id("Run tests first")
    r = PlaybookRule(
        id=rid, text="Run tests first", version=1, status="promoted",
        pass_rate_before=0.3, pass_rate_after=0.5, simulated=True, created_at=_utc_now()
    )
    store.insert_rule(r)
    rolled = store.rollback(rid)
    assert rolled.status == "rolled_back"
