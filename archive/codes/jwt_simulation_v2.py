import time
import jwt
import random
import json
import threading
import paho.mqtt.client as mqtt
import matplotlib.pyplot as plt

NUM_NODES = 10
MSGS_PER_NODE = 15
ENERGY_PER_BYTE = 0.001
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
TOPIC = "iot/biometric/jwt"
JWT_SECRET = "my_jwt_secret_key"

energy_consumption_jwt = {node: 0.0 for node in range(NUM_NODES)}
lock = threading.Lock()
trusted_database = {i: i * 1000 + 1234 for i in range(NUM_NODES)}


def iot_node_jwt(node_id):
    client = mqtt.Client()
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()

    for _ in range(MSGS_PER_NODE):
        time.sleep(random.uniform(0.5, 2))
        biometric_value = random.randint(1000, 9999)
        timestamp = time.time()

        payload = {
            "node_id": node_id,
            "timestamp": timestamp,
            "biometric": biometric_value,
        }

        token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        packet = json.dumps({"jwt": token})
        msg_bytes = packet.encode("utf-8")

        with lock:
            energy_consumption_jwt[node_id] += len(msg_bytes) * ENERGY_PER_BYTE

        print(
            f"[Node {node_id}] Sent JWT | Energy: {len(msg_bytes)*ENERGY_PER_BYTE:.3f} mJ"
        )
        client.publish(TOPIC, packet)

    client.loop_stop()
    client.disconnect()


def gateway_jwt():
    client = mqtt.Client()

    def on_connect(client, userdata, flags, rc):
        client.subscribe(TOPIC)

    def on_message(client, userdata, msg):
        message = json.loads(msg.payload.decode("utf-8"))
        try:
            decoded = jwt.decode(message["jwt"], JWT_SECRET, algorithms=["HS256"])
            node_id = decoded["node_id"]
            biometric = decoded["biometric"]
            ref_val = trusted_database.get(node_id, None)
            match_status = (
                "MATCH" if ref_val and abs(ref_val - biometric) < 100 else "NO MATCH"
            )
            print(
                f"[Gateway-JWT] Node {node_id} Biometric: {biometric} → {match_status}"
            )
        except jwt.exceptions.InvalidTokenError:
            print("[Gateway-JWT] Invalid JWT")

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
    time.sleep((MSGS_PER_NODE + 5) * NUM_NODES)
    client.loop_stop()
    client.disconnect()


if __name__ == "__main__":
    threads = []

    gw_thread = threading.Thread(target=gateway_jwt)
    gw_thread.start()
    threads.append(gw_thread)

    for node_id in range(NUM_NODES):
        t = threading.Thread(target=iot_node_jwt, args=(node_id,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    print("\nTotal Energy Consumption (mJ) - JWT:")
    for node, energy in energy_consumption_jwt.items():
        print(f"Node {node}: {energy:.2f} mJ")

    nodes = list(energy_consumption_jwt.keys())
    energy_values = list(energy_consumption_jwt.values())
    plt.figure(figsize=(8, 4))
    plt.bar(nodes, energy_values, color="orange")
    plt.xlabel("Node ID")
    plt.ylabel("Energy Consumed (mJ)")
    plt.title("Energy Consumption per Node - JWT Authentication")
    plt.grid(axis="y")
    plt.tight_layout()
    plt.show()
