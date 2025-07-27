import time
import tenseal as ts
import paho.mqtt.client as mqtt
import base64
import random

from settings import (
    MQTT_PORT,
    MQTT_BROKER,
    BATTERY_DEFAULT_VALUE,
    MSGS_PER_NODE,
    FHE_INTERVAL,
    BATTERY_THRESHOLD,
    ENERGY_PER_BYTE,
    TOPIC,
)

from ...core import generate_hmac
from ...utils import compress_data


def iot_node(
    node_id, context, lock, energy_consumption, mqtt_broker=None, mqtt_port=None
):
    mqtt_broker = mqtt_broker or MQTT_BROKER
    mqtt_port = mqtt_port or MQTT_PORT
    client = mqtt.Client()
    client.connect(mqtt_broker, mqtt_port, 60)
    client.loop_start()

    battery_level = BATTERY_DEFAULT_VALUE
    batch_plain = []

    for msg_count in range(1, MSGS_PER_NODE + 1):
        time.sleep(random.uniform(0.5, 2))
        biometric_value = random.randint(1000, 9999)
        timestamp = round(time.time(), 3)
        message_light = f"{node_id}:{timestamp}:{biometric_value}"
        signature = generate_hmac(message_light)

        battery_level -= random.randint(1, 2)

        payload = None
        msg_bytes = None
        encoded_compressed = None

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
            encoded_compressed = compress_data(payload)
            # msg_bytes = payload_str.encode('utf-8')
            msg_bytes = encoded_compressed.encode("utf-8")
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
                encoded_compressed = compress_data(payload)
                # msg_bytes = payload_str.encode('utf-8')
                msg_bytes = encoded_compressed.encode("utf-8")
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

        send_time_ns = time.time_ns()
        payload["send_time_ns"] = send_time_ns
        # qos=1 ensures message delivery
        # client.publish(TOPIC, payload_str, qos=1)
        client.publish(TOPIC, encoded_compressed, qos=1)

    client.loop_stop()
    client.disconnect()
