#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export DEMO_MODE=true
export PYTHONPATH=backend
python3 -m playbookforge.cli seed
python3 -m playbookforge.cli export --out data/dashboard_export.json
