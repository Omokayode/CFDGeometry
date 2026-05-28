#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${PYTHONPATH:-}:src"
cfd-geometry domain -o examples/milwaukee-kilbourn/data \
  --place "Kilbourn Avenue, Milwaukee, Wisconsin, USA" \
  --dem --terrain
