import time
import tenseal as ts
import paho.mqtt.client as mqtt
import json
import base64
import random

from settings import (
    MQTT_PORT,
    MQTT_BROKER,
    MSGS_PER_NODE,
    ENERGY_PER_BYTE,
    TOPIC,
)

from ...core import generate_hmac


def iot_node(
    node_id, context, lock, energy_consumption, mqtt_broker=None, mqtt_port=None
):
    mqtt_broker = mqtt_broker or MQTT_BROKER
    mqtt_port = mqtt_port or MQTT_PORT
    client = mqtt.Client()
    client.connect(mqtt_broker, mqtt_port, 60)
    client.loop_start()

    for _ in range(MSGS_PER_NODE):
        time.sleep(random.uniform(0.5, 2))
        biometric_value = random.randint(1000, 9999)
        timestamp = round(time.time(), 3)
        message_light = f"{node_id}:{timestamp}:{biometric_value}"
        signature = generate_hmac(message_light)

        enc_vec = ts.bfv_vector(context, [biometric_value])
        serialized_enc = base64.b64encode(enc_vec.serialize()).decode("utf-8")

        payload = {
            "node_id": node_id,
            "battery_level": 100,
            "hmac": signature,
            "timestamp": timestamp,
            "enc_biometric": serialized_enc,
        }
        send_time_ns = time.time_ns()
        payload["send_time_ns"] = send_time_ns
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
