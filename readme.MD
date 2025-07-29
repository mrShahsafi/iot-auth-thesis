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
(venv) ➜  main git:(dev) ✗ ./run_multiple_nodes_enhanced.sh 
```