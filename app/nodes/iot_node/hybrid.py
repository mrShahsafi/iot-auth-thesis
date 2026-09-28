import base64
import random
import time

import paho.mqtt.client as mqtt
import tenseal as ts

from settings import (
    MQTT_PORT,
    MQTT_BROKER,
    BATTERY_DEFAULT_VALUE,
    MSGS_PER_NODE,
    FHE_INTERVAL,
    BATTERY_THRESHOLD,
    ENERGY_PER_BYTE,
    IMPOSTOR_RATE,
    REPLAY_RATE,
    TOPIC,
)

from ...core import ack_decisions, generate_hmac, hmac_message, wait_for_decisions
from ...utils import compress_data


def iot_node(
    node_id,
    context,
    lock,
    energy_consumption,
    mqtt_broker=None,
    mqtt_port=None,
    trusted_database=None,
):
    """One reading = one authentication sample (a quantized feature vector). k = FHE_INTERVAL consecutive
    readings are packed into one BFV ciphertext; the last partial batch is flushed so every reading is sent."""
    client = mqtt.Client()
    client.connect(mqtt_broker or MQTT_BROKER, mqtt_port or MQTT_PORT, 60)
    client.loop_start()
    outstanding = set()  # t_capture_first of batches awaiting the gateway's decision
    ack_decisions(client, node_id, lock, energy_consumption, outstanding)

    record = trusted_database[node_id]
    battery_level = BATTERY_DEFAULT_VALUE
    batch, last_message = [], None

    def publish(batch, battery_level, encrypted):
        nonlocal last_message
        payload = {
            "node_id": node_id,
            "battery_level": battery_level,
            "batch_size": len(batch),
            "batch_timestamps": [b["ts"] for b in batch],
            "batch_HMAC": [b["hmac"] for b in batch],
            "labels": [int(b["genuine"]) for b in batch],  # simulation ground truth, not part of the protocol
            "t_capture_first": batch[0]["ts"],
            "t_capture_last": batch[-1]["ts"],
        }
        if encrypted:
            t0 = time.time()
            enc = ts.bfv_vector(context, [x for b in batch for x in b["vec"]])
            payload["enc_biometrics"] = base64.b64encode(enc.serialize()).decode("utf-8")
            payload["t_enc_start"], payload["t_enc_end"] = t0, time.time()
        else:
            payload["type"] = "light"  # battery low: HMAC-only ping, no biometric data
        payload["t_publish"] = time.time()
        encoded = compress_data(payload)
        with lock:
            energy_consumption[node_id] += len(encoded) * ENERGY_PER_BYTE
        if encrypted:
            outstanding.add(batch[0]["ts"])
        client.publish(TOPIC, encoded, qos=1)
        print(f"[Node {node_id}] Sent {'BATCH' if encrypted else 'LIGHT'} ({len(batch)} readings) | "
              f"{len(encoded)} B | Battery: {battery_level}")
        if last_message is not None and random.random() < REPLAY_RATE:
            client.publish(TOPIC, last_message, qos=1)  # attacker replays an earlier message verbatim
        last_message = encoded

    for msg_count in range(1, MSGS_PER_NODE + 1):
        time.sleep(random.uniform(0.5, 2))
        genuine = random.random() >= IMPOSTOR_RATE
        vec = random.choice(record["genuine"] if genuine else record["impostor"])
        timestamp = round(time.time(), 3)
        batch.append({"vec": vec, "ts": timestamp, "genuine": genuine,
                      "hmac": generate_hmac(hmac_message(node_id, timestamp, vec), node_id)})
        battery_level -= random.randint(1, 2)
        if msg_count % FHE_INTERVAL == 0:
            publish(batch, battery_level, encrypted=True)
            batch = []
        elif battery_level < BATTERY_THRESHOLD:
            publish(batch, battery_level, encrypted=False)
            batch = []
    if batch:
        publish(batch, battery_level, encrypted=True)

    wait_for_decisions(outstanding)
    time.sleep(1)
    client.loop_stop()
    client.disconnect()
