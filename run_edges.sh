#!/usr/bin/env bash
# Throw every edge-case diff at the tool and report crash / hang / clean.
#
#   ./run_edges.sh                               # uses: python gemma_ollama.py
#   TOOL="python gemma_ollama.py" ./run_edges.sh # override if your script differs
#   TOOL="python gemma_ollama.py --pass commit" ./run_edges.sh   # single pass = faster
#
# A per-case timeout guards against hangs so one stuck run can't freeze the suite.

DIR="$(cd "$(dirname "$0")" && pwd)"
TOOL="${TOOL:-python gemma_ollama.py}"
PER_CASE_TIMEOUT="${PER_CASE_TIMEOUT:-180}"   # seconds

# pick a timeout command (macOS needs `brew install coreutils` -> gtimeout)
TO="timeout"; command -v gtimeout >/dev/null && TO="gtimeout"
command -v "$TO" >/dev/null || TO=""

for f in "$DIR"/edge_cases/*.diff; do
  name="$(basename "$f")"
  printf '%-26s ' "$name"
  if [ -n "$TO" ]; then
    out="$($TO "$PER_CASE_TIMEOUT" $TOOL "$f" 2>&1)"; rc=$?
  else
    out="$($TOOL "$f" 2>&1)"; rc=$?
  fi
  if [ $rc -eq 124 ]; then
    echo "HANG (killed after ${PER_CASE_TIMEOUT}s) <-- bug: needs a timeout"
  elif echo "$out" | grep -qiE 'traceback|unhandled|Error: .*line [0-9]'; then
    echo "CRASH <-- bug: $(echo "$out" | grep -iE 'Error' | head -1)"
  else
    echo "ok"
  fi
done