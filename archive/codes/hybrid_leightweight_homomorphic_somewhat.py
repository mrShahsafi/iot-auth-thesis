import simpy
import random
import hashlib
import hmac
import tenseal as ts

NUM_NODES = 10
SIM_TIME = 100
ENERGY_PER_BYTE = 0.001
SHARED_SECRET = b"my_shared_secret_key"

# تنظیم رمزنگاری Somewhat Homomorphic Encryption با پارامترهای سبک‌تر
# (مثلاً poly_modulus_degree کمتر و plain_modulus مناسب)
context = ts.context(
    ts.SCHEME_TYPE.BFV, poly_modulus_degree=4096, plain_modulus=1032193
)
context.generate_galois_keys()
context.generate_relin_keys()
context.global_scale = 2**40

total_energy_consumed_she = {node: 0.0 for node in range(NUM_NODES)}
total_latency_she = []

trusted_database = {i: i * 1000 + 1234 for i in range(NUM_NODES)}


def iot_node_she(env, node_id, gateway_pipe):
    while True:
        yield env.timeout(random.randint(20, 40))  # فرکانس ارسال کاهش یافته
        biometric_value = random.randint(1000, 9999)

        # مرحله سبک‌وزن: ارسال اطلاعات هویت و امضای HMAC
        message = f"{node_id}:{env.now}"
        signature = hmac.new(
            SHARED_SECRET, message.encode(), hashlib.sha256
        ).hexdigest()
        packet_light = f"{message}:{signature}"
        size_light = len(packet_light.encode("utf-8"))
        energy_light = size_light * ENERGY_PER_BYTE

        # مرحله رمزنگاری Somewhat: فقط رمزنگاری بخشی از داده (مثلاً فقط بیت‌های کم اهمیت‌تر)
        # برای سادگی، فرض می‌کنیم فقط نصف داده رمزنگاری شود (مثال مفهومی)
        partial_value = biometric_value // 2
        enc_vec = ts.bfv_vector(context, [partial_value])
        serialized_enc = enc_vec.serialize()
        size_she = len(serialized_enc)
        energy_she = size_she * ENERGY_PER_BYTE

        total_energy_consumed_she[node_id] += energy_light + energy_she

        print(
            f"[Time {env.now}] Node {node_id} sends lightweight + Somewhat HE data | Energy used: {energy_light + energy_she:.3f} mJ"
        )
        yield gateway_pipe.put(
            (env.now, node_id, packet_light, serialized_enc, biometric_value)
        )


def gateway_she(env, gateway_pipe):
    while True:
        (
            timestamp,
            sender,
            packet_light,
            serialized_enc,
            original_value,
        ) = yield gateway_pipe.get()
        latency = env.now - timestamp
        total_latency_she.append(latency)

        # اعتبارسنجی HMAC
        try:
            parts = packet_light.split(":")
            node_id = int(parts[0])
            sent_time = float(parts[1])
            signature = parts[2]
            message = f"{node_id}:{sent_time}"
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

        # پردازش رمزنگاری Somewhat
        enc_vec = ts.bfv_vector_from(context, serialized_enc)
        decrypted_partial = enc_vec.decrypt()[0]

        # بازسازی مقدار اصلی (مثلاً با تقریب)
        reconstructed_value = decrypted_partial * 2  # فرض ساده برای بازسازی

        # مقایسه با مقدار مرجع
        ref_val = trusted_database.get(node_id, None)
        match_status = (
            "MATCH" if abs(ref_val - reconstructed_value) < 100 else "NO MATCH"
        )

        print(
            f"[Time {env.now}] Gateway authenticates Node {sender} (Latency: {latency}s) → {match_status}"
        )


env = simpy.Environment()
gateway_pipe = simpy.Store(env)

for node in range(NUM_NODES):
    env.process(iot_node_she(env, node, gateway_pipe))

env.process(gateway_she(env, gateway_pipe))

env.run(until=SIM_TIME)

print("\n--- Somewhat Homomorphic Encryption Hybrid Simulation Summary ---")
for node, energy in total_energy_consumed_she.items():
    print(f"Node {node}: {energy:.2f} mJ")
avg_latency = (
    sum(total_latency_she) / len(total_latency_she) if total_latency_she else 0
)
print(f"Average Latency: {avg_latency:.2f} seconds")
