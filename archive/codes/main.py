import networkx as nx
import simpy
import random
import matplotlib.pyplot as plt
import tenseal as ts

# پارامترهای عمومی
NUM_NODES = 10  # تعداد گره‌های IoT
SIM_TIME = 100  # زمان شبیه‌سازی
ENERGY_PER_BYTE = 0.001  # میلی ژول به ازای هر بایت انتقال داده

# ساختار گراف شبکه
G = nx.erdos_renyi_graph(n=NUM_NODES, p=0.3)
G.add_node("gateway")
for node in range(NUM_NODES):
    G.add_edge(node, "gateway")

# آمار مصرف انرژی و تأخیر
total_energy_consumed = {node: 0.0 for node in range(NUM_NODES)}
total_latency = []

# تنظیم رمزنگاری BFV
context = ts.context(
    ts.SCHEME_TYPE.BFV, poly_modulus_degree=8192, plain_modulus=1032193
)
context.generate_galois_keys()
context.generate_relin_keys()
context.global_scale = 2**40

# تابع تولید داده و ارسال
def iot_node(env, node_id, gateway_pipe):
    while True:
        yield env.timeout(random.randint(5, 15))
        biometric_value = random.randint(1000, 9999)  # داده عددی بیومتریک
        encrypted_data = ts.bfv_vector(context, [biometric_value])
        data_size = len(str(encrypted_data.serialize()))
        energy = data_size * ENERGY_PER_BYTE
        total_energy_consumed[node_id] += energy
        print(
            f"[Time {env.now}] Node {node_id} sends encrypted biometric value to Gateway | Value: {biometric_value} | Energy used: {energy:.3f} mJ"
        )
        yield gateway_pipe.put((env.now, node_id, encrypted_data.serialize()))


# تابع دریافت داده در Gateway
trusted_database = {
    i: i * 1000 + 1234 for i in range(NUM_NODES)
}  # داده بیومتریک مرجع هر کاربر


def gateway(env, gateway_pipe):
    while True:
        timestamp, sender, encrypted_payload = yield gateway_pipe.get()
        latency = env.now - timestamp
        total_latency.append(latency)
        enc_vec = ts.bfv_vector_from(context, encrypted_payload)
        # مقایسه ساده با مقدار مرجع
        ref_val = trusted_database[sender]
        ref_enc = ts.bfv_vector(context, [ref_val])
        diff = enc_vec - ref_enc
        decrypted = diff.decrypt()[0]
        match_status = "MATCH" if decrypted == 0 else "NO MATCH"
        print(
            f"[Time {env.now}] Gateway received from Node {sender} (Latency: {latency}s) → Authentication: {match_status}"
        )


# شبیه‌سازی
env = simpy.Environment()
gateway_pipe = simpy.Store(env)

for node in range(NUM_NODES):
    env.process(iot_node(env, node, gateway_pipe))

env.process(gateway(env, gateway_pipe))

env.run(until=SIM_TIME)

# خروجی نهایی
print("\n--- Simulation Summary ---")
print("Total Energy Consumed (mJ):")
for node, energy in total_energy_consumed.items():
    print(f"Node {node}: {energy:.2f} mJ")

avg_latency = sum(total_latency) / len(total_latency) if total_latency else 0
print(f"\nAverage Latency: {avg_latency:.2f} seconds")

# نمودار مصرف انرژی
nodes = list(total_energy_consumed.keys())
energy_values = list(total_energy_consumed.values())

plt.figure(figsize=(10, 5))
plt.bar(nodes, energy_values, color="skyblue")
plt.xlabel("Node ID")
plt.ylabel("Energy Consumed (mJ)")
plt.title("Energy Consumption per IoT Node")
plt.grid(True)
plt.tight_layout()
plt.show()
