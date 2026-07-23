import simpy
import random
import hashlib
import hmac
import tenseal as ts

NUM_NODES = 10
SIM_TIME = 100
ENERGY_PER_BYTE = 0.001
SHARED_SECRET = b"my_shared_secret_key"

# تنظیم رمزنگاری BFV
context = ts.context(
    ts.SCHEME_TYPE.BFV, poly_modulus_degree=4096, plain_modulus=1032193
)
context.generate_galois_keys()
context.generate_relin_keys()
context.global_scale = 2**40

total_energy_consumed_hybrid = {node: 0.0 for node in range(NUM_NODES)}
total_latency_hybrid = []

trusted_database = {i: i * 1000 + 1234 for i in range(NUM_NODES)}


def iot_node_hybrid(env, node_id, gateway_pipe):
    while True:
        yield env.timeout(random.randint(50, 100))
        biometric_value = random.randint(1000, 9999)
        # مرحله سبک‌وزن: تولید پیام HMAC
        message = f"{node_id}:{biometric_value}:{env.now}"
        signature = hmac.new(
            SHARED_SECRET, message.encode(), hashlib.sha256
        ).hexdigest()
        packet_light = f"{message}:{signature}"
        size_light = len(packet_light.encode("utf-8"))
        energy_light = size_light * ENERGY_PER_BYTE
        total_energy_consumed_hybrid[node_id] += energy_light

        # مرحله رمزنگاری همومورفیک روی داده حساس (مثلاً فقط مقدار بیومتریک)
        enc_vec = ts.bfv_vector(context, [biometric_value])
        serialized_enc = enc_vec.serialize()
        size_he = len(serialized_enc)
        energy_he = size_he * ENERGY_PER_BYTE
        total_energy_consumed_hybrid[node_id] += energy_he

        print(
            f"[Time {env.now}] Node {node_id} sends lightweight + HE data | Energy used: {energy_light + energy_he:.3f} mJ"
        )
        yield gateway_pipe.put((env.now, node_id, packet_light, serialized_enc))


def gateway_hybrid(env, gateway_pipe):
    while True:
        timestamp, sender, packet_light, serialized_enc = yield gateway_pipe.get()
        latency = env.now - timestamp
        total_latency_hybrid.append(latency)

        # اعتبارسنجی HMAC
        try:
            parts = packet_light.split(":")
            node_id = int(parts[0])
            biometric = int(parts[1])
            sent_time = float(parts[2])
            signature = parts[3]
            message = f"{node_id}:{biometric}:{sent_time}"
            expected_signature = hmac.new(
                SHARED_SECRET, message.encode(), hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(signature, expected_signature):
                print(f"[Time {env.now}] Invalid HMAC signature from Node {sender}")
                continue
        except:
            print(
                f"[Time {env.now}] Error parsing lightweight message from Node {sender}"
            )
            continue

        # پردازش رمزنگاری همومورفیک
        enc_vec = ts.bfv_vector_from(context, serialized_enc)
        ref_val = trusted_database.get(node_id, None)
        ref_enc = ts.bfv_vector(context, [ref_val])
        diff = enc_vec - ref_enc
        decrypted = diff.decrypt()[0]
        match_status = "MATCH" if decrypted == 0 else "NO MATCH"
        print(
            f"[Time {env.now}] Gateway authenticates Node {sender} (Latency: {latency}s) → {match_status}"
        )


env = simpy.Environment()
gateway_pipe = simpy.Store(env)

for node in range(NUM_NODES):
    env.process(iot_node_hybrid(env, node, gateway_pipe))

env.process(gateway_hybrid(env, gateway_pipe))

env.run(until=SIM_TIME)

print("\n--- Hybrid Simulation Summary ---")
for node, energy in total_energy_consumed_hybrid.items():
    print(f"Node {node}: {energy:.2f} mJ")
avg_latency = (
    sum(total_latency_hybrid) / len(total_latency_hybrid) if total_latency_hybrid else 0
)
print(f"Average Latency: {avg_latency:.2f} seconds")
