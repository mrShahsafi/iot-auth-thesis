import time
import hmac
import tenseal as ts
import paho.mqtt.client as mqtt
import json
import base64
import gzip

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

    def on_connect(client, userdata, flags, rc):
        client.subscribe(TOPIC)

    def on_message(client, userdata, msg):
        if MODE == "Hybrid":
            compressed_payload = base64.b64decode(msg.payload)
            decompressed_json = gzip.decompress(compressed_payload).decode("utf-8")
            payload = json.loads(decompressed_json)
        else:
            payload = json.loads(msg.payload.decode("utf-8"))
        receive_time_ns = time.time_ns()
        node_id = payload["node_id"]

        if "enc_biometrics" in payload:
            base_latency = receive_time_ns - payload["batch_timestamps"][0] * 1e9
            latency_ms = base_latency / 1_000_000
        else:
            latency_ms = (receive_time_ns - payload["send_time_ns"]) / 1_000_000

        try:
            with open(LOG_CSV, "a", newline="") as f:
                f.write(
                    f"{node_id},{latency_ms:.2f},{len(msg.payload)},{payload.get('battery_level',-1)},{payload.get('energy',0):.3f}\n"
                )
        except Exception as e:
            print(f"[Gateway] Write CSV ERROR: {e}")

        # if not is_fresh(node_id, timestamp):
        #     print(f"[Gateway] Replay detected from Node {node_id}")
        #     return

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

    def is_fresh(node_id, ts):
        dq = recent_timestamps[node_id]
        now = time.time()
        while dq and now - dq[0] > REPLAY_WINDOW_SEC:
            dq.popleft()
        if ts in dq:
            return False
        dq.append(ts)
        return True

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
    time.sleep((MSGS_PER_NODE + 5) * NUM_NODES)
    client.loop_stop()
    client.disconnect()
