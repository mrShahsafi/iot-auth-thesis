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

# ---------- تنظیمات ----------
NUM_NODES = 3  # تعداد نودها
MSGS_PER_NODE = 10  # پیام برای هر نود
ENERGY_PER_BYTE = 0.001  # میلی ژول به ازای هر بایت
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
TOPIC = "iot/biometric"
SHARED_SECRET = b"my_shared_secret_key"

context = ts.context(
    ts.SCHEME_TYPE.BFV, poly_modulus_degree=8192, plain_modulus=1032193
)
context.generate_galois_keys()
context.generate_relin_keys()
context.global_scale = 2**40

# ---------- متغیرها ----------
energy_consumption = {node: 0.0 for node in range(NUM_NODES)}
lock = threading.Lock()  # برای همگام‌سازی دسترسی به متغیر مشترک انرژی

# ---------- HMAC ----------
def generate_hmac(message: str) -> str:
    return hmac.new(SHARED_SECRET, message.encode(), hashlib.sha256).hexdigest()


# ---------- IOT NODE ----------
def iot_node(node_id):
    client = mqtt.Client()
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
    for _ in range(MSGS_PER_NODE):
        time.sleep(1 + node_id)  # زمان ارسال متنوع برای هریک
        biometric_value = random.randint(1000, 9999)
        enc_vec = ts.bfv_vector(context, [biometric_value])
        serialized_enc = enc_vec.serialize()
        timestamp = time.time()
        message_light = f"{node_id}:{timestamp}"
        signature = generate_hmac(message_light)
        payload = {
            "node_id": node_id,
            "timestamp": timestamp,
            "hmac": signature,
            "enc_biometric": base64.b64encode(serialized_enc).decode("utf-8"),
        }
        payload_str = json.dumps(payload)
        msg_bytes = payload_str.encode("utf-8")
        # هر پیام خروجی نسبت به حجم، مصرف انرژی دارد
        with lock:
            energy_consumption[node_id] += len(msg_bytes) * ENERGY_PER_BYTE
        print(
            f"[Node {node_id}] Energy for this msg: {len(msg_bytes)*ENERGY_PER_BYTE:.3f} mJ, Total: {energy_consumption[node_id]:.3f} mJ"
        )
        client.publish(TOPIC, payload_str)
    client.loop_stop()
    client.disconnect()


# ---------- GATEWAY ----------
def gateway():
    client = mqtt.Client()

    def on_connect(client, userdata, flags, rc):
        print("[Gateway] Connected.")
        client.subscribe(TOPIC)

    def on_message(client, userdata, msg):
        # فرایند عادی اعتبارسنجی و رمزگشایی
        pass  # بدنه این بخش قبلاً دارید و روی انرژی تاثیر ندارد.

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
    time.sleep((MSGS_PER_NODE + 2) * NUM_NODES)  # زمان کافی برای دریافت همه پیام‌ها
    client.loop_stop()
    client.disconnect()


# ---------- اجرا ----------
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

    # ----- رسم نمودار -----
    nodes = list(energy_consumption.keys())
    energy_values = list(energy_consumption.values())
    print("\nTotal Energy Consumption (mJ):")
    for node, energy in energy_consumption.items():
        print(f"Node {node}: {energy:.2f} mJ")
    plt.figure(figsize=(8, 4))
    plt.bar(nodes, energy_values, color="orange")
    plt.xlabel("Node ID")
    plt.ylabel("Energy Consumed (mJ)")
    plt.title("Energy Consumption per IoT Node (Homomorphic + MQTT)")
    plt.grid(axis="y")
    plt.tight_layout()
    plt.show()
