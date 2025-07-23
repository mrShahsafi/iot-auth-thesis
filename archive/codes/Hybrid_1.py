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
FHE_INTERVAL = 5  # هر ۵ پیام یکبار FHE
BATTERY_THRESHOLD = 20  # اگر باتری کمتر از ۲۰ درصد شد، فقط HMAC

"""
	•	هر ۵ پیام یکبار رمزنگاری FHE بر کل batch:‌ حجم را کاهش می‌دهد و انرژی جمعی کمتر مصرف می‌شود.
	•	در صورت پایین بودن باتری، به‌صورت تطبیقی فقط HMAC ارسال می‌شود، الگوریتم همچنان batchهای ۵تایی را رعایت می‌کند.
	•	در دفعات دیگر اطلاعات batch شده فقط ذخیره می‌شوند، و ارسال نمی‌شوند تا batch کامل شود.
	•	مصرف انرژی هر پیام براساس اندازه بایت محاسبه و جمع می‌شود.
	•	نمودار مصرف انرژی برای هر نود رسم می‌شود.
"""

context = ts.context(
    ts.SCHEME_TYPE.BFV, poly_modulus_degree=4096, plain_modulus=1032193
)
context.generate_galois_keys()
context.generate_relin_keys()
context.global_scale = 2**40

energy_consumption = {node: 0.0 for node in range(NUM_NODES)}
lock = threading.Lock()


def generate_hmac(message: str) -> str:
    return hmac.new(SHARED_SECRET, message.encode(), hashlib.sha256).hexdigest()


def iot_node(node_id):
    client = mqtt.Client()
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()

    battery_level = 20  # باتری را ۱۰۰ درصد شروع می‌کنیم
    batch_plain = []
    fhe_counter = 0

    for msg_count in range(1, MSGS_PER_NODE + 1):
        time.sleep(random.uniform(0.5, 2))  # فاصله زمانی هر ارسال
        biometric_value = random.randint(1000, 9999)
        timestamp = time.time()
        message_light = f"{node_id}:{timestamp}:{biometric_value}"
        signature = generate_hmac(message_light)

        # کاستن باتری طبق یک مدل ساده: هر پیام ۱ یا ۲ درصد مصرف
        battery_level -= random.randint(1, 2)

        payload = None
        msg_bytes = None

        # رفتار batching adaptive:
        if msg_count % FHE_INTERVAL == 0:
            # اگر باتری پایین هم باشد هر ۵ بار باید FHE ارسال شود
            batch_plain.append(
                {
                    "biometric": biometric_value,
                    "timestamp": timestamp,
                    "hmac": signature,
                }
            )
            # پیام‌های batch شده را رمزنگاری و یکجا ارسال کن
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
            batch_plain = []  # بعد ارسال batch بافر را خالی کن

        else:
            # اگر باتری کمتر از آستانه باشد فقط HMAC (بدون رمزنگاری FHE)
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
                # هر پیام عادی هم برای batching نگه می‌داریم، ولی نمی‌فرستیم تا به مضرب FHE_INTERVAL برسیم
                batch_plain.append(
                    {
                        "biometric": biometric_value,
                        "timestamp": timestamp,
                        "hmac": signature,
                    }
                )
                continue  # چیزی ارسال نشود تا batch کامل شود

        with lock:
            energy_consumption[node_id] += len(msg_bytes) * ENERGY_PER_BYTE

        client.publish(TOPIC, payload_str)

    client.loop_stop()
    client.disconnect()


def gateway():
    client = mqtt.Client()

    def on_connect(client, userdata, flags, rc):
        client.subscribe(TOPIC)

    def on_message(client, userdata, msg):
        # پیاده‌سازی کامل برای سرور در این مثال حذف شده (مطابق با قبلی عمل شود)
        pass

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

    # نمودار انرژی
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
