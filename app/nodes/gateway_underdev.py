import time
import hmac
import tenseal as ts
import paho.mqtt.client as mqtt
import json
import base64
import gzip

from collections import deque


from settings import (
    TOPIC,
    REPLAY_WINDOW_SEC,
    MQTT_PORT,
    MQTT_BROKER,
    MSGS_PER_NODE,
    NUM_NODES,
    LOG_CSV,
    MODE,
)
from ..core import generate_hmac


def gateway(context, trusted_database, recent_timestamps):
    client = mqtt.Client()
    received_count = 0
    expected_count = NUM_NODES * MSGS_PER_NODE

    def on_connect(client, userdata, flags, rc):
        client.subscribe(TOPIC)

    def on_message(client, userdata, msg):
        nonlocal received_count
        try:
            if MODE == "Hybrid":
                compressed_payload = base64.b64decode(msg.payload)
                decompressed_json = gzip.decompress(compressed_payload).decode("utf-8")
                payload = json.loads(decompressed_json)
            else:
                payload = json.loads(msg.payload.decode("utf-8"))
        except (EOFError, gzip.BadGzipFile, UnicodeDecodeError, json.JSONDecodeError) as e:
            print(f"[Gateway] Error in decompressing/parsing message: {e}")
            return  # Skip this corrupted or incomplete message
        receive_time_ns = time.time_ns()
        node_id = payload["node_id"]
        timestamp = (
            payload.get("timestamp") or payload.get("batch_timestamps", [None])[0]
        )
        if "enc_biometrics" in payload:
            base_latency = receive_time_ns - payload["batch_timestamps"][0] * 1e9
            latency_ms = base_latency / 1_000_000

        else:
            latency_ms = (receive_time_ns - payload["send_time_ns"]) / 1_000_000

        if not is_fresh(node_id, timestamp):
            print(f"[Gateway] Replay detected from Node {node_id}")
            return

        received_count += 1
        try:
            with open(LOG_CSV, "a", newline="") as f:
                f.write(
                    f"{node_id},{latency_ms:.2f},{len(msg.payload)},{payload.get('battery_level',-1)},{payload.get('energy',0):.3f}\n"
                )
        except Exception as e:
            print(f"[Gateway] Write CSV ERROR: {e}")

        if "enc_biometrics" in payload:
            enc_bytes = base64.b64decode(payload["enc_biometrics"])
            dec_start = time.time()
            vec = ts.bfv_vector_from(context, enc_bytes)
            decrypted_values = vec.decrypt()
            dec_time = time.time() - dec_start
            print(
                f"[Gateway] Received BATCH from Node {node_id} | Decryption Time: {dec_time:.4f} sec"
            )

            for i, val in enumerate(decrypted_values):
                timestamp = payload["batch_timestamps"][i]
                hmac_expected = generate_hmac(f"{node_id}:{timestamp}:{val}")
                valid = hmac.compare_digest(payload["batch_HMAC"][i], hmac_expected)
                ref_val = trusted_database.get(node_id, None)
                match_status = (
                    "MATCH" if ref_val and abs(ref_val - val) < 100 else "NO MATCH"
                )
                print(f"→ Biometric: {val} | HMAC: {valid} | Match: {match_status}")
                print(f"[Gateway] {trusted_database}")
        elif payload.get("type") == "light":
            biometric = payload["biometric"]
            timestamp = payload["timestamp"]
            hmac_expected = generate_hmac(f"{node_id}:{timestamp}:{biometric}")
            valid = hmac.compare_digest(payload["hmac"], hmac_expected)
            ref_val = trusted_database.get(node_id, None)
            match_status = (
                "MATCH" if ref_val and abs(ref_val - biometric) < 100 else "NO MATCH"
            )
            print(
                f"[Gateway] Light AUTH from Node {node_id} | HMAC: {valid} | Match: {match_status}"
            )

        if received_count >= expected_count:
            print(f"[Gateway] Received all {expected_count} messages. Stopping loop.")
            client.loop_stop()

    def is_fresh(node_id, ts):
        # Initialize deque for new node_ids
        # Replay Attack
        if node_id not in recent_timestamps:
            recent_timestamps[node_id] = deque()

        dq = recent_timestamps[node_id]
        now = time.time()

        # Convert timestamp to float if it's a string
        try:
            ts_float = float(ts) if ts is not None else now
        except (ValueError, TypeError):
            # If conversion fails, treat as current time
            ts_float = now

        # Convert REPLAY_WINDOW_SEC to float in case it's a string
        try:
            replay_window = float(REPLAY_WINDOW_SEC)
        except (ValueError, TypeError):
            replay_window = 60.0  # Default fallback

        # Remove old timestamps outside the replay window
        # Handle potential conversion errors for existing timestamps
        while dq:
            try:
                oldest_ts = float(dq[0])
                if now - oldest_ts > replay_window:
                    dq.popleft()
                else:
                    break
            except (ValueError, TypeError):
                # Remove invalid timestamp that can't be converted
                dq.popleft()

        # Check if timestamp already exists (replay attack)
        if ts_float in dq:
            return False

        # Add new timestamp
        dq.append(ts_float)
        return True

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
    # time.sleep((MSGS_PER_NODE + 5) * NUM_NODES)
    # client.loop_stop()
    client.loop_forever()  # This will block and run until loop_stop() is called inside on_message
    client.disconnect()
