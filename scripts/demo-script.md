# PlaybookForge — 3-minute demo script

> Read times are approximate. Run `npm run dev` first (DEMO_MODE). Dashboard: http://127.0.0.1:43123

| Time | Narration | Action |
|------|-----------|--------|
| 0:00–0:20 | "Coding agents repeat mistakes because failures aren't captured as tested playbook rules. PlaybookForge ingests traces, distils rules, and replay-tests them before promotion." | Show browser on dashboard header + **Simulated agent benchmarks** badge. |
| 0:20–0:45 | "On seed, we ingested sample JSONL traces — generic, Claude Code, and OpenHands shapes — and distilled five candidate rules offline." | Scroll **Rule timeline**; point at version badges and example rule text. |
| 0:45–1:15 | "The replay harness runs our bundled ten-task Python suite baseline versus rule-injected prompts, tracking pass rate, tokens, and time." | Highlight stat cards and **Pass rate before / after** bar chart; stress **simulated** label. |
| 1:15–1:45 | "Per-task diffs show where a rule helped or regressed — promotion is blocked on any regression." | Scroll **Per-task diff** table; mention task-02 config scenario. |
| 1:45–2:15 | "I'll replay a candidate to refresh metrics, then promote through the gate — versions land in SQLite." | Click **Replay**, then **Promote** on a row; toast confirmation. |
| 2:15–2:40 | "Rollback is one click — every version is reversible for safe experimentation." | Click **Rollback**; timeline shows `rolled_back`. |
| 2:40–3:00 | "With API keys and DEMO_MODE off, the same pipeline calls OpenAI or Anthropic for live distillation. Repo includes tests, CLI, and MIT license — built Nov 6–15 for HackerSquad." | Optional: show terminal `npm test`; end on dashboard. |
