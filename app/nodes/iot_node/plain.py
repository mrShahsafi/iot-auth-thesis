import base64
import json
import random
import time

import paho.mqtt.client as mqtt
import tenseal as ts

from settings import (
    MQTT_PORT,
    MQTT_BROKER,
    MSGS_PER_NODE,
    ENERGY_PER_BYTE,
    IMPOSTOR_RATE,
    TOPIC,
)

from ...core import ack_decisions, generate_hmac, hmac_message, wait_for_decisions


def iot_node(
    node_id, context, lock, energy_consumption, mqtt_broker=None, mqtt_port=None, trusted_database=None
):
    """Unbatched baseline: every reading is encrypted and published on its own, as uncompressed JSON."""
    client = mqtt.Client()
    client.connect(mqtt_broker or MQTT_BROKER, mqtt_port or MQTT_PORT, 60)
    client.loop_start()
    outstanding = set()
    ack_decisions(client, node_id, lock, energy_consumption, outstanding)
    record = trusted_database[node_id]

    for _ in range(MSGS_PER_NODE):
        time.sleep(random.uniform(0.5, 2))
        genuine = random.random() >= IMPOSTOR_RATE
        vec = random.choice(record["genuine"] if genuine else record["impostor"])
        timestamp = round(time.time(), 3)
        t0 = time.time()
        enc = ts.bfv_vector(context, vec)
        payload = {
            "node_id": node_id,
            "battery_level": 100,
            "batch_size": 1,
            "batch_timestamps": [timestamp],
            "batch_HMAC": [generate_hmac(hmac_message(node_id, timestamp, vec), node_id)],
            "labels": [int(genuine)],
            "t_capture_first": timestamp,
            "t_capture_last": timestamp,
            "enc_biometrics": base64.b64encode(enc.serialize()).decode("utf-8"),
            "t_enc_start": t0,
            "t_enc_end": time.time(),
            "t_publish": time.time(),
        }
        payload_str = json.dumps(payload)
        with lock:
            energy_consumption[node_id] += len(payload_str) * ENERGY_PER_BYTE
        outstanding.add(timestamp)
        client.publish(TOPIC, payload_str, qos=1)
        print(f"[Node {node_id}] Sent FHE + HMAC | {len(payload_str)} B")

    wait_for_decisions(outstanding)
    time.sleep(1)
    client.loop_stop()
    client.disconnect()
