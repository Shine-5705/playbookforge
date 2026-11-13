# PlaybookForge — Devpost-style submission

## Elevator pitch

PlaybookForge captures what coding agents get wrong, distils **playbook rules** from failure traces, and **proves** them with a replay harness before promotion — versioned in SQLite with one-click rollback.

## Problem & users

**Problem:** Autonomous coding agents forget lessons between runs. Teams re-pay the same token and debug tax when agents skip tests, edit config first, or ship partial fixes.

**Users:** Hackathon participants, agent platform builders, and engineering leads shipping coding agents who need **governed, measurable** prompt/playbook evolution.

## What we built

1. **Trace ingest** — JSONL with generic schema plus adapters for Claude Code and OpenHands-style logs (`backend/playbookforge/ingest.py`).
2. **LLM distillation** — Candidate rules from failed traces via OpenAI/Anthropic env keys, with `DEMO_MODE` deterministic fallback (`distill.py`).
3. **Replay harness** — Python suite re-runs 10 bundled micro-tasks with/without each rule, recording pass rate, tokens, and wall time (`replay.py`).
4. **Promotion gate** — Rules promote only if aggregate pass rate improves **and** no task regresses (`promote.py`).
5. **Dashboard** — Next.js UI: rule timeline, before/after chart, per-task diffs, promote/rollback (`components/playbook-dashboard.tsx`).

## AI functionality

| Step | AI role |
|------|---------|
| Distillation | LLM reads failed trace summaries and proposes imperative playbook rules (JSON `rules[]`). |
| Demo fallback | Regex/heuristic extraction mirrors LLM output when `DEMO_MODE=true` or keys are absent. |
| Replay | In demo, a **simulated agent** models pass-rate lift; with keys off demo, stubs run real pytest per task. |

Live distillation example prompt intent: *“Extract concise playbook rules from failed agent traces.”*

## Demo

1. `npm install && npm run dev`
2. Dashboard shows **Simulated agent benchmarks** badge.
3. Click **Replay** on a candidate rule → chart updates.
4. **Promote** if gate passes; **Rollback** restores prior version.

See `scripts/demo-script.md` for a 3-minute narrated walkthrough.

## What's next

- Wire replay to real Cursor/Claude Code trace export webhooks
- Team-scoped rule namespaces and PR bot that injects promoted rules
- Multi-rule composition and conflict detection
- Confidence intervals over N stochastic agent replays (non-demo)

## Team

**Shine Gupta** — [@Shine-5705](https://github.com/Shine-5705), Adaply
