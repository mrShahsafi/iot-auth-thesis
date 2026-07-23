import time
import hmac
import hashlib
import tenseal as ts
import paho.mqtt.client as mqtt
import json
import threading
import base64
import random
import matplotlib.pyplot as plt
from collections import defaultdict, deque

NUM_NODES = 50
MSGS_PER_NODE = 15
ENERGY_PER_BYTE = 0.001
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
TOPIC = "iot/biometric"
SHARED_SECRET = b"my_shared_secret_key"
FHE_INTERVAL = 5
BATTERY_THRESHOLD = 20
BATTERY_DEFAULT_VALUE = 100
POLY_MOD_DEGREE = 4096

OUTPUT_FILE = "metrics_log_for_Hybrid_2_new_changesPy.csv"
REPLAY_WINDOW_SEC = 60
MODE = "Hybrid"

context = ts.context(
    ts.SCHEME_TYPE.BFV, poly_modulus_degree=POLY_MOD_DEGREE, plain_modulus=1032193
)
context.generate_galois_keys()
context.generate_relin_keys()
context.global_scale = 2**40

energy_consumption = {node: 0.0 for node in range(NUM_NODES)}
recent_timestamps = defaultdict(lambda: deque(maxlen=100))
with open(OUTPUT_FILE, "w", newline="") as f:
    f.write("node_id,latency_ms,bytes,battery\n")

lock = threading.Lock()
trusted_database = {i: i * 1000 + 1234 for i in range(NUM_NODES)}


def generate_hmac(message: str) -> str:
    return hmac.new(SHARED_SECRET, message.encode(), hashlib.sha256).hexdigest()


def iot_node(node_id):
    client = mqtt.Client()
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()

    battery_level = BATTERY_DEFAULT_VALUE
    batch_plain = []

    for msg_count in range(1, MSGS_PER_NODE + 1):
        time.sleep(random.uniform(0.5, 2))
        biometric_value = random.randint(1000, 9999)
        timestamp = time.time()
        message_light = f"{node_id}:{timestamp}:{biometric_value}"
        signature = generate_hmac(message_light)

        battery_level -= random.randint(1, 2)

        payload = None
        msg_bytes = None

        if msg_count % FHE_INTERVAL == 0:
            batch_plain.append(
                {
                    "biometric": biometric_value,
                    "timestamp": timestamp,
                    "hmac": signature,
                }
            )
            enc_batch = [entry["biometric"] for entry in batch_plain]
            enc_vec = ts.bfv_vector(context, enc_batch)
            serialized_enc = base64.b64encode(enc_vec.serialize()).decode("utf-8")

            payload = {
                "node_id": node_id,
                "battery_level": battery_level,
                "batch_HMAC": [entry["hmac"] for entry in batch_plain],
                "batch_timestamps": [entry["timestamp"] for entry in batch_plain],
                "enc_biometrics": serialized_enc,
                "batch_size": len(batch_plain),
            }
            payload_str = json.dumps(payload)
            msg_bytes = payload_str.encode("utf-8")
            print(
                f"[Node {node_id}] Sent BATCH with FHE ({len(batch_plain)} recs) | Energy: {len(msg_bytes)*ENERGY_PER_BYTE:.3f} mJ | Battery: {battery_level}"
            )
            batch_plain = []

        else:
            if battery_level < BATTERY_THRESHOLD:
                payload = {
                    "node_id": node_id,
                    "type": "light",
                    "battery_level": battery_level,
                    "hmac": signature,
                    "timestamp": timestamp,
                    "biometric": biometric_value,
                }
                payload_str = json.dumps(payload)
                msg_bytes = payload_str.encode("utf-8")
                print(
                    f"[Node {node_id}] Sent ONLY HMAC (Battery Low) | Energy: {len(msg_bytes)*ENERGY_PER_BYTE:.3f} mJ | Battery: {battery_level}"
                )
            else:
                batch_plain.append(
                    {
                        "biometric": biometric_value,
                        "timestamp": timestamp,
                        "hmac": signature,
                    }
                )
                continue

        with lock:
            energy_consumption[node_id] += len(msg_bytes) * ENERGY_PER_BYTE

        send_time_ns = time.time_ns()  # زمان دقیق نانوثانیه
        payload["send_time_ns"] = send_time_ns
        payload_str = json.dumps(payload)
        msg_bytes = payload_str.encode("utf-8")
        # qos=1 ensures message delivery
        client.publish(TOPIC, payload_str, qos=1)

    client.loop_stop()
    client.disconnect()


def gateway():
    client = mqtt.Client()

    def on_connect(client, userdata, flags, rc):
        client.subscribe(TOPIC)

    def on_message(client, userdata, msg):
        payload = json.loads(msg.payload.decode("utf-8"))
        receive_time_ns = time.time_ns()
        node_id = payload["node_id"]

        if "enc_biometrics" in payload:
            base_latency = (
                receive_time_ns - payload["batch_timestamps"][0] * 1e9
            )  # اولین رکورد
            latency_ms = base_latency / 1_000_000
        else:
            latency_ms = (receive_time_ns - payload["send_time_ns"]) / 1_000_000

        try:
            with open(OUTPUT_FILE, "a", newline="") as f:
                f.write(
                    f"{node_id},{latency_ms:.2f},{len(msg.payload)},{payload.get('battery_level',-1)}\n"
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


if __name__ == "__main__":
    threads = []

    gw_thread = threading.Thread(target=gateway)
    gw_thread.start()
    threads.append(gw_thread)

    for node_id in range(NUM_NODES):
        t = threading.Thread(target=iot_node, args=(node_id,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    nodes = list(energy_consumption.keys())
    energy_values = list(energy_consumption.values())
    print("\nTotal Energy Consumption (mJ):")
    for node, energy in energy_consumption.items():
        print(f"Node {node}: {energy:.2f} mJ")
    plt.figure(figsize=(8, 4))
    plt.bar(nodes, energy_values, color="purple")
    plt.xlabel("Node ID")
    plt.ylabel("Energy Consumed (mJ)")
    plt.title("Energy Consumption per Node - Adaptive Batching & Crypto")
    plt.grid(axis="y")
    plt.tight_layout()
    plt.show()
