import simpy
import random
import hashlib
import hmac
import matplotlib.pyplot as plt

# پارامترهای عمومی
NUM_NODES = 10
SIM_TIME = 100
ENERGY_PER_BYTE = 0.001  # میلی ژول به ازای هر بایت انتقال داده
SHARED_SECRET = b"my_shared_secret_key"  # کلید مشترک برای HMAC

# آمار مصرف انرژی و تأخیر
total_energy_consumed_light = {node: 0.0 for node in range(NUM_NODES)}
total_latency_light = []

# تابع تولید داده و ارسال پیام احراز هویت سبک‌وزن
def iot_node_light(env, node_id, gateway_pipe):
    while True:
        yield env.timeout(random.randint(50, 100))
        biometric_value = random.randint(1000, 9999)
        message = f"{node_id}:{biometric_value}:{env.now}"
        # تولید کد HMAC به عنوان امضای پیام
        signature = hmac.new(
            SHARED_SECRET, message.encode(), hashlib.sha256
        ).hexdigest()
        packet = f"{message}:{signature}"
        data_size = len(packet.encode("utf-8"))
        energy = data_size * ENERGY_PER_BYTE
        total_energy_consumed_light[node_id] += energy
        print(
            f"[Time {env.now}] Node {node_id} sends lightweight auth message to Gateway | Biometric: {biometric_value} | Energy used: {energy:.3f} mJ"
        )
        yield gateway_pipe.put((env.now, node_id, packet))


# تابع دریافت و اعتبارسنجی پیام در Gateway
trusted_database = {i: i * 1000 + 1234 for i in range(NUM_NODES)}


def gateway_light(env, gateway_pipe):
    while True:
        timestamp, sender, packet = yield gateway_pipe.get()
        latency = env.now - timestamp
        total_latency_light.append(latency)
        try:
            parts = packet.split(":")
            node_id = int(parts[0])
            biometric = int(parts[1])
            sent_time = float(parts[2])
            signature = parts[3]
            message = f"{node_id}:{biometric}:{sent_time}"
            # اعتبارسنجی HMAC
            expected_signature = hmac.new(
                SHARED_SECRET, message.encode(), hashlib.sha256
            ).hexdigest()
            if hmac.compare_digest(signature, expected_signature):
                ref_val = trusted_database.get(node_id, None)
                match_status = "MATCH" if ref_val == biometric else "NO MATCH"
            else:
                match_status = "INVALID SIGNATURE"
        except Exception as e:
            match_status = "ERROR"
        print(
            f"[Time {env.now}] Gateway received lightweight auth from Node {sender} (Latency: {latency}s) → Authentication: {match_status}"
        )


# شبیه‌سازی
env = simpy.Environment()
gateway_pipe = simpy.Store(env)

for node in range(NUM_NODES):
    env.process(iot_node_light(env, node, gateway_pipe))

env.process(gateway_light(env, gateway_pipe))

env.run(until=SIM_TIME)

# خروجی نهایی
print("\n--- Lightweight Auth Simulation Summary ---")
print("Total Energy Consumed (mJ):")
for node, energy in total_energy_consumed_light.items():
    print(f"Node {node}: {energy:.2f} mJ")

avg_latency = (
    sum(total_latency_light) / len(total_latency_light) if total_latency_light else 0
)
print(f"\nAverage Latency: {avg_latency:.2f} seconds")

# نمودار مصرف انرژی
nodes = list(total_energy_consumed_light.keys())
energy_values = list(total_energy_consumed_light.values())

plt.figure(figsize=(10, 5))
plt.bar(nodes, energy_values, color="green")
plt.xlabel("Node ID")
plt.ylabel("Energy Consumed (mJ)")
plt.title("Energy Consumption per IoT Node (Lightweight Auth)")
plt.grid(True)
plt.tight_layout()
plt.show()
