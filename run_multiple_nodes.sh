#!/bin/bash
# X4 sweep for the journal revision. Requires a local Mosquitto broker on localhost:1883.
#   10 nodes x 15 readings, k = 1..10, three repetitions   (Table 4, latency decomposition, FAR/FRR online)
#   50 nodes at k = 1 and k = 10                             (Table 6, scalability)
#   Plain baseline: every reading in its own uncompressed message
# Logs: output/revision/logs/metrics_log_<MODE>_<NODES>_<MSGS>_<E/B>_<k>_<BATT>_<N>_<RUN>.csv
set -e
cd "$(dirname "$0")"
PY=${PY:-venv/bin/python3}
export MPLBACKEND=Agg POLY_MOD_DEGREE=4096 MSGS_PER_NODE=15 MODE=Hybrid

for run in 1 2 3; do
  for k in 1 2 3 4 5 6 7 8 9 10; do
    echo "== Hybrid 10 nodes k=$k run=$run"
    RUN_ID=$run FHE_INTERVAL=$k NUM_NODES=10 $PY -m app.run 2>&1 | grep -E "Gateway\] [0-9]+/|Total:"
  done
done
for k in 1 10; do
  echo "== Hybrid 50 nodes k=$k"
  RUN_ID=1 FHE_INTERVAL=$k NUM_NODES=50 $PY -m app.run 2>&1 | grep -E "Gateway\] [0-9]+/|Total:"
done
echo "== Plain 10 nodes"
RUN_ID=1 MODE=Plain FHE_INTERVAL=1 NUM_NODES=10 $PY -m app.run 2>&1 | grep -E "Gateway\] [0-9]+/|Total:"
echo "All runs completed -> output/revision/logs"
