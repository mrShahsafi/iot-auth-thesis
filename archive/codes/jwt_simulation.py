import simpy
import random
import jwt  # pip install PyJWT
import time
import matplotlib.pyplot as plt

# پارامترهای عمومی
NUM_NODES = 10
SIM_TIME = 100
ENERGY_PER_BYTE = 0.001  # میلی ژول به ازای هر بایت انتقال داده
SECRET_KEY = "my_secret_key"  # کلید مخفی برای امضای JWT

# آمار مصرف انرژی و تأخیر
total_energy_consumed_jwt = {node: 0.0 for node in range(NUM_NODES)}
total_latency_jwt = []

# تابع تولید داده و ارسال JWT
def iot_node_jwt(env, node_id, gateway_pipe):
    while True:
        yield env.timeout(random.randint(5, 15))
        biometric_value = random.randint(1000, 9999)
        payload = {
            "node_id": node_id,
            "biometric": biometric_value,
            "timestamp": env.now,
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
        data_size = len(token.encode("utf-8"))
        energy = data_size * ENERGY_PER_BYTE
        total_energy_consumed_jwt[node_id] += energy
        print(
            f"[Time {env.now}] Node {node_id} sends JWT token to Gateway | Biometric: {biometric_value} | Energy used: {energy:.3f} mJ"
        )
        yield gateway_pipe.put((env.now, node_id, token))


# تابع دریافت و اعتبارسنجی JWT در Gateway
trusted_database = {i: i * 1000 + 1234 for i in range(NUM_NODES)}


def gateway_jwt(env, gateway_pipe):
    while True:
        timestamp, sender, token = yield gateway_pipe.get()
        latency = env.now - timestamp
        total_latency_jwt.append(latency)
        try:
            decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            ref_val = trusted_database.get(decoded["node_id"], None)
            match_status = "MATCH" if ref_val == decoded["biometric"] else "NO MATCH"
        except jwt.InvalidTokenError:
            match_status = "INVALID TOKEN"
        print(
            f"[Time {env.now}] Gateway received JWT from Node {sender} (Latency: {latency}s) → Authentication: {match_status}"
        )


# شبیه‌سازی
env = simpy.Environment()
gateway_pipe = simpy.Store(env)

for node in range(NUM_NODES):
    env.process(iot_node_jwt(env, node, gateway_pipe))

env.process(gateway_jwt(env, gateway_pipe))

env.run(until=SIM_TIME)

# خروجی نهایی
print("\n--- JWT Simulation Summary ---")
print("Total Energy Consumed (mJ):")
for node, energy in total_energy_consumed_jwt.items():
    print(f"Node {node}: {energy:.2f} mJ")

avg_latency = (
    sum(total_latency_jwt) / len(total_latency_jwt) if total_latency_jwt else 0
)
print(f"\nAverage Latency: {avg_latency:.2f} seconds")

# نمودار مصرف انرژی
nodes = list(total_energy_consumed_jwt.keys())
energy_values = list(total_energy_consumed_jwt.values())

plt.figure(figsize=(10, 5))
plt.bar(nodes, energy_values, color="orange")
plt.xlabel("Node ID")
plt.ylabel("Energy Consumed (mJ)")
plt.title("Energy Consumption per IoT Node (JWT)")
plt.grid(True)
plt.tight_layout()
plt.show()
