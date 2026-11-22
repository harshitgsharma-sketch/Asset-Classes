#!/usr/bin/env bash
# Re-run every oscillator in the project's run order. Each engine reads its inputs
# from models/ and rewrites its score log (deterministic: same inputs, same scores).
set -euo pipefail
cd "$(dirname "$0")/../models"
for engine in gold nifty sector global asset_class commodities btc fixed_income carry factor stock real_assets; do
  echo "== ${engine}_oscillator.py"
  MPLBACKEND=Agg python3 -I "${engine}_oscillator.py" all > "/tmp/${engine}.log"
done
echo "all engines ran"
