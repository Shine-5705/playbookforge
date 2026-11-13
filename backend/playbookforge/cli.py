from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import __version__
from .distill import llm_distill_rules, persist_candidates
from .ingest import ingest_jsonl
from .promote import apply_replay_to_candidate, promote_rule
from .replay import replay_rule, report_to_dict, run_task_tests
from .store import PlaybookStore


def _default_db() -> Path:
    root = Path(__file__).resolve().parents[2]
    return root / "data" / "playbookforge.db"


def _default_data() -> Path:
    return Path(__file__).resolve().parents[2] / "data"


def cmd_seed(args: argparse.Namespace) -> int:
    """Seed demo data: ingest sample traces, distill rules, run simulated replays."""
    os.environ.setdefault("DEMO_MODE", "true")
    data = _default_data()
    store = PlaybookStore(_default_db())
    traces = ingest_jsonl(data / "sample_traces.jsonl")
    rules, simulated = llm_distill_rules(traces)
    candidates = persist_candidates(store, rules, simulated)
    store.set_meta("last_seed", "demo")
    for c in candidates:
        report = replay_rule(c, force_simulated=True)
        apply_replay_to_candidate(store, c, report)
    print(json.dumps({"rules": len(candidates), "simulated": simulated}, indent=2))
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    path = Path(args.path)
    traces = ingest_jsonl(path, adapter=args.adapter)
    out = Path(args.out) if args.out else _default_data() / "ingested.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            [
                {
                    "run_id": t.run_id,
                    "task_id": t.task_id,
                    "success": t.success,
                    "source": t.source,
                    "events": [{"kind": e.kind, "message": e.message} for e in t.events],
                }
                for t in traces
            ],
            indent=2,
        )
    )
    print(f"Ingested {len(traces)} traces -> {out}")
    return 0


def cmd_distill(args: argparse.Namespace) -> int:
    path = Path(args.traces)
    traces = ingest_jsonl(path, adapter=args.adapter)
    store = PlaybookStore(_default_db())
    rules, simulated = llm_distill_rules(traces)
    created = persist_candidates(store, rules, simulated)
    print(json.dumps({"rules": [r.text for r in created], "simulated": simulated}, indent=2))
    return 0


def cmd_replay(args: argparse.Namespace) -> int:
    store = PlaybookStore(_default_db())
    rule = store.get_rule(args.rule_id, args.version)
    if not rule:
        print("Rule not found", file=sys.stderr)
        return 1
    report = replay_rule(rule)
    updated = apply_replay_to_candidate(store, rule, report)
    print(json.dumps({"rule_version": updated.version, **report_to_dict(report)}, indent=2))
    return 0


def cmd_promote(args: argparse.Namespace) -> int:
    store = PlaybookStore(_default_db())
    try:
        promoted = promote_rule(store, args.rule_id, args.version)
        print(json.dumps({"status": promoted.status, "version": promoted.version}, indent=2))
    except Exception as exc:  # noqa: BLE001
        print(str(exc), file=sys.stderr)
        return 1
    return 0


def cmd_rollback(args: argparse.Namespace) -> int:
    store = PlaybookStore(_default_db())
    rolled = store.rollback(args.rule_id)
    print(json.dumps({"status": rolled.status, "version": rolled.version}, indent=2))
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    store = PlaybookStore(_default_db())
    payload = {
        "rules": [
            {
                "id": r.id,
                "version": r.version,
                "text": r.text,
                "status": r.status,
                "pass_rate_before": r.pass_rate_before,
                "pass_rate_after": r.pass_rate_after,
                "simulated": r.simulated,
                "created_at": r.created_at,
                "parent_version": r.parent_version,
            }
            for r in store.list_rules()
        ],
        "latest_replay": store.latest_replay(),
        "demo_mode": os.environ.get("DEMO_MODE", "true"),
    }
    out = Path(args.out) if args.out else _default_data() / "dashboard_export.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2))
    print(out)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="pf", description="PlaybookForge CLI")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    seed = sub.add_parser("seed", help="Seed demo database")
    seed.set_defaults(func=cmd_seed)

    ingest = sub.add_parser("ingest", help="Ingest JSONL traces")
    ingest.add_argument("path")
    ingest.add_argument("--adapter", default="auto")
    ingest.add_argument("--out", default="")
    ingest.set_defaults(func=cmd_ingest)

    distill = sub.add_parser("distill", help="Distill rules from traces")
    distill.add_argument("traces")
    distill.add_argument("--adapter", default="auto")
    distill.set_defaults(func=cmd_distill)

    replay = sub.add_parser("replay", help="Replay suite with/without rule")
    replay.add_argument("rule_id")
    replay.add_argument("--version", type=int, default=None)
    replay.set_defaults(func=cmd_replay)

    promote = sub.add_parser("promote", help="Promote rule after replay gate")
    promote.add_argument("rule_id")
    promote.add_argument("--version", type=int, required=True)
    promote.set_defaults(func=cmd_promote)

    rollback = sub.add_parser("rollback", help="Rollback rule one version")
    rollback.add_argument("rule_id")
    rollback.set_defaults(func=cmd_rollback)

    export = sub.add_parser("export", help="Export dashboard JSON")
    export.add_argument("--out", default="")
    export.set_defaults(func=cmd_export)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
