# Basic usage with just mode
```bash
python -m app.run --mode=Hybrid
```

# Full example with multiple parameters
```bash
python -m app.run --mode=Hybrid --num-nodes=15 --msgs-per-node=20 --energy-per-byte=0.002
```

# All available options:
```bash
python -m app.run \
  --mode=Hybrid \
  --num-nodes=10 \
  --msgs-per-node=15 \
  --energy-per-byte=0.001 \
  --mqtt-broker=localhost \
  --mqtt-port=1883 \
  --topic=iot/biometric \
  --shared-secret=my_shared_secret_key \
  --fhe-interval=5 \
  --battery-threshold=20 \
  --battery-default=100 \
  --poly-mod-degree=4096
  ```
---
# Run in different batch_sizes:
```bash
(venv) ➜  main git:(dev) ✗ ./run_multiple_nodes.sh 
```


## Codebase layout

```
app/
  run.py            entrypoint: `python -m app.run --mode=Hybrid ...`
  executor.py        main(): spins up gateway thread + N IoT node threads
  initializer.py      init_app(): builds TenSEAL context, energy dict,
                       replay-timestamp tracker, trusted biometric DB
  core/
    tenseal.py         tensor_context(): BFV context (poly_modulus_degree,
                        plain_modulus=1032193, galois/relin keys)
    encryption.py       generate_hmac(): HMAC-SHA256 over "node:ts:value"
    biometrics.py       generate_biometric_vector(): loads fingerprint
                        vectors (HOG features from settings/fingerprints/
                        *.tif) or synthetic random values as the
                        "trusted database" ground truth per node
    energy.py           init_energy_consumption(): per-node energy dict
    auth.py             (currently empty — placeholder)
  nodes/
    gateway.py          MQTT subscriber: decompress/decode payload, verify
                        HMAC + replay freshness, BFV-decrypt batch, log
                        latency/bytes/battery/energy to LOG_CSV, print
                        MATCH/NO MATCH per value
    gateway_underdev.py  WIP/alternate gateway implementation (not wired
                        into executor.py — treat as experimental)
    iot_node/
      hybrid.py          "Hybrid" mode node: batches biometric readings,
                        every FHE_INTERVAL-th message BFV-encrypts+sends
                        the batch; otherwise sends lightweight HMAC-only
                        pings (or buffers if battery is healthy); simulates
                        battery drain and occasional "false biometric"
                        readings
      plain.py           "Plain" mode node: baseline, encrypts+sends every
                        single message individually (no batching) — the
                        comparison baseline for the "traditional" method
  utils/
    parser.py            CLI arg parsing (mirrors settings/base.py keys)
    compress.py           compress_data(): gzip + base64 the JSON payload
                        before MQTT publish (mimics lightweight framing)
    metrics.py            create_output_csv(): initializes LOG_CSV header
    plot.py (894 lines)   all matplotlib/seaborn plotting used for the
                        thesis figures (energy vs batch size, latency
                        boxplots, 3D plots, correlation heatmaps, feature
                        importance, batch-efficiency summary, etc.)
    plot_executer.py       CLI-style driver for one specific plot
    quadratic_regressoin.py estimate_latency/energy/combined_cost helper
                        curve-fits used in some plots
    setup.py               setup_plot_latency_energy_vs_batch_size_data():
                        aggregates per-batch-size CSV logs for plotting
settings/
  base.py              central config: MODE, NUM_NODES, MSGS_PER_NODE,
                        ENERGY_PER_BYTE, MQTT_BROKER/PORT, TOPIC,
                        SHARED_SECRET, FHE_INTERVAL, BATTERY_THRESHOLD/
                        DEFAULT_VALUE, POLY_MOD_DEGREE, REPLAY_WINDOW_SEC,
                        DRY_RUN — priority: CLI args > env vars > defaults
                        (see get_setting()); also builds LOG_CSV path
  local.py             optional local overrides (imported if present)
  fingerprints/        FVC2002-style fingerprint image dataset (*.tif),
                        108 subjects x 8 impressions
analysis.ipynb         Jupyter notebook: loads output/ CSVs, trains
                        RandomForest/MLP/XGBoost models, produces the
                        Chapter 4 plots and metrics saved to
                        output/analysis/
output/
  logs/                 per-run metrics_log_<MODE>_<NUM_NODES>_
                        <MSGS_PER_NODE>_<ENERGY_PER_BYTE>_<FHE_INTERVAL>_
                        <BATTERY_THRESHOLD>.csv — columns:
                        node_id,latency_ms,bytes,battery,energy
  plots/                generated figures (energy, latency boxplots, 3D
                        plots, batch efficiency)
  analysis/             ML model outputs: trained .pkl models (RF/MLP per
                        target: energy, latency_ms, communication_cost),
                        norm_scaler.pkl, model_metrics.csv, feature
                        importance + correlation heatmap PNGs
  batch_efficiency_summary.csv  aggregated batch-size sweep results
archive/                earlier/superseded implementations kept for
                        history: Paillier-based, lightweight-only, no-
                        encryption baseline, JWT simulations, hybrid v1/v2
                        iterations. Not used by the current app/ code path
                        — don't wire new features into these.
run_multiple_nodes.sh   shell driver that sweeps batch sizes / node counts
                        to produce the full set of output/logs/*.csv used
                        by analysis.ipynb and the thesis figures
thesis.pages            the actual thesis manuscript (Apple Pages format,
                        Persian + English abstract). See "Reading
                        thesis.pages" below.
```

## Running the simulation

```bash
# Basic
python -m app.run --mode=Hybrid

# Full parameter sweep example
python -m app.run \
  --mode=Hybrid \
  --num-nodes=10 \
  --msgs-per-node=15 \
  --energy-per-byte=0.001 \
  --mqtt-broker=localhost \
  --mqtt-port=1883 \
  --topic=iot/biometric \
  --shared-secret=my_shared_secret_key \
  --fhe-interval=5 \
  --battery-threshold=20 \
  --battery-default=100 \
  --poly-mod-degree=4096

# Batch-size sweep used to generate the thesis figures
./run_multiple_nodes.sh
```

Requires a running MQTT broker (e.g. local Mosquitto) on `MQTT_BROKER:
MQTT_PORT`. `--mode=Plain` runs the unbatched baseline (`iot_node/plain.py`)
for comparison against `--mode=Hybrid`.

Python env: `venv/` (Python 3.9) has all deps installed (`tenseal`,
`paho-mqtt`, `scikit-image`, pandas/numpy/sklearn/matplotlib/seaborn, etc.)
— prefer `venv/bin/python3` over system Python when running/debugging code
in this repo.


## The research problem and proposed solution

- **Problem:** IoT biometric authentication needs strong confidentiality
  (fingerprint templates can't be revoked if leaked), but homomorphic
  encryption — which lets a server match encrypted templates without ever
  decrypting them — causes severe **ciphertext expansion**, which is
  expensive for battery- and bandwidth-constrained edge nodes.
- **Proposed hybrid approach:** combine
  1. **BFV fully-homomorphic encryption** (via Microsoft SEAL / TenSEAL) —
     server-side matching happens on ciphertexts, never plaintext.
  2. **MQTT** as the lightweight pub/sub transport (tiny headers,
     publish-then-sleep radio behavior).
  3. **Batching / SIMD slot packing** — pack multiple biometric feature
     values into a single BFV ciphertext (`ts.bfv_vector(context, [...])`)
     and aggregate several messages before transmitting, amortizing the
     fixed per-ciphertext overhead.
- **Architecture (3 layers):** IoT node (feature extraction + BFV
  encryption) → MQTT broker / gateway (batching, HMAC + replay-freshness
  check, homomorphic decrypt-and-match) → conceptually a cloud/server layer
  for heavier homomorphic computation (in this codebase the gateway plays
  that matching role directly).
- **Evaluation method:** SimPy-style event simulation via Python
  `threading` (IoT nodes + gateway as threads) for the crypto/application
  layer, intended alongside an NS-3 network-layer simulation (IEEE
  802.15.4, up to 150 nodes) per the thesis — NS-3 artifacts are not part
  of this Python codebase; the network-behavior claims in the thesis rely
  on separate NS-3 runs and metric derivation. Fingerprint data comes from
  the Kaggle FVC2002 fingerprint dataset (`settings/fingerprints/*.tif`),
  processed per ISO/IEC 19794-2 minutiae-format ideas (HOG features used
  here as the feature-vector stand-in).
- **Metrics tracked:** communication cost (bytes/messages), energy (mJ,
  modeled as `bytes * ENERGY_PER_BYTE`), end-to-end latency (ms), battery
  level, and match/replay-attack outcomes.
- **ML analysis (Chapter 4):** Random Forest / MLP / XGBoost regressors
  trained on simulation logs to predict energy, latency, and communication
  cost from parameters like batch size and payload bytes, plus feature
  importance and Pearson correlation analysis.
