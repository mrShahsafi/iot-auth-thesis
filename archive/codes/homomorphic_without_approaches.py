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

NUM_NODES = 10
MSGS_PER_NODE = 15
ENERGY_PER_BYTE = 0.001
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
TOPIC = "iot/biometric"
SHARED_SECRET = b"my_shared_secret_key"

context = ts.context(
    ts.SCHEME_TYPE.BFV, poly_modulus_degree=4096, plain_modulus=1032193
)
context.generate_galois_keys()
context.generate_relin_keys()
context.global_scale = 2**40

energy_consumption = {node: 0.0 for node in range(NUM_NODES)}
lock = threading.Lock()
trusted_database = {i: i * 1000 + 1234 for i in range(NUM_NODES)}


def generate_hmac(message: str) -> str:
    return hmac.new(SHARED_SECRET, message.encode(), hashlib.sha256).hexdigest()


def iot_node(node_id):
    client = mqtt.Client()
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()

    for _ in range(MSGS_PER_NODE):
        time.sleep(random.uniform(0.5, 2))
        biometric_value = random.randint(1000, 9999)
        timestamp = time.time()
        message_light = f"{node_id}:{timestamp}:{biometric_value}"
        signature = generate_hmac(message_light)

        enc_vec = ts.bfv_vector(context, [biometric_value])
        serialized_enc = base64.b64encode(enc_vec.serialize()).decode("utf-8")

        payload = {
            "node_id": node_id,
            "battery_level": 100,  # ثابت چون adaptive نیست
            "hmac": signature,
            "timestamp": timestamp,
            "enc_biometric": serialized_enc,
        }
        payload_str = json.dumps(payload)
        msg_bytes = payload_str.encode("utf-8")

        with lock:
            energy_consumption[node_id] += len(msg_bytes) * ENERGY_PER_BYTE

        print(
            f"[Node {node_id}] Sent FHE + HMAC | Energy: {len(msg_bytes)*ENERGY_PER_BYTE:.3f} mJ"
        )
        client.publish(TOPIC, payload_str)

    client.loop_stop()
    client.disconnect()


def gateway():
    client = mqtt.Client()

    def on_connect(client, userdata, flags, rc):
        client.subscribe(TOPIC)

    def on_message(client, userdata, msg):
        payload = json.loads(msg.payload.decode("utf-8"))
        node_id = payload["node_id"]
        timestamp = payload["timestamp"]
        enc_bytes = base64.b64decode(payload["enc_biometric"])

        dec_start = time.time()
        vec = ts.bfv_vector_from(context, enc_bytes)
        decrypted_val = vec.decrypt()[0]
        dec_time = time.time() - dec_start

        hmac_expected = generate_hmac(f"{node_id}:{timestamp}:{decrypted_val}")
        valid = hmac.compare_digest(payload["hmac"], hmac_expected)
        ref_val = trusted_database.get(node_id, None)
        match_status = (
            "MATCH" if ref_val and abs(ref_val - decrypted_val) < 100 else "NO MATCH"
        )

        print(
            f"[Gateway] FHE AUTH from Node {node_id} | Biometric: {decrypted_val} | HMAC: {valid} | Match: {match_status} | Decrypt Time: {dec_time:.4f} sec"
        )

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
    plt.bar(nodes, energy_values, color="blue")
    plt.xlabel("Node ID")
    plt.ylabel("Energy Consumed (mJ)")
    plt.title("Energy Consumption per Node - Full FHE + HMAC")
    plt.grid(axis="y")
    plt.tight_layout()
    plt.show()
