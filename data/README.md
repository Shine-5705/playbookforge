# Data directory (sample / simulated only)

Nothing in this folder is confidential production telemetry. All fixtures are **synthetic** and exist to power offline hackathon demos.

| File | Label | Description |
|------|-------|-------------|
| `sample_traces.jsonl` | **Sample traces** | Fictional agent run records (generic, Claude Code, OpenHands shapes) for ingest and distillation demos. |
| `dashboard_export.json` | **Simulated export** | Cached rules and replay payloads for the Next.js dashboard; metrics include `"simulated": true` when generated under `DEMO_MODE=true`. |
| `playbookforge.db` | **Local runtime** | Created by `seed` / `npm run dev` (gitignored); not shipped as authoritative state. |

Regenerate demo state:

```bash
export DEMO_MODE=true PYTHONPATH=backend
bash scripts/seed-demo.sh
```