"""X1: BFV parameter profile for the paper (C11).

    venv/bin/python3 eval/he_profile.py            -> output/revision/bfv_params.csv, bfv_sizes.csv

Reports, for N in {4096, 8192} with the plaintext modulus used by app/core/tenseal.py:
coefficient-modulus chain, slot count, security level, fresh noise budget, multiplicative
depth, key sizes, and ciphertext / MQTT-payload bytes for k = 1..10 packed readings.
"""
import base64
import csv
import sys
import time
from pathlib import Path

import tenseal as ts
import tenseal.sealapi as sa

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.utils.compress import compress_data  # noqa: E402

OUT = ROOT / "output" / "revision"
PLAIN_MODULUS = 1032193
K_RANGE = range(1, 11)


def seal_profile(n):
    parms = sa.EncryptionParameters(sa.SCHEME_TYPE.BFV)
    parms.set_poly_modulus_degree(n)
    chain = sa.CoeffModulus.BFVDefault(n, sa.SEC_LEVEL_TYPE.TC128)
    parms.set_coeff_modulus(chain)
    parms.set_plain_modulus(sa.Modulus(PLAIN_MODULUS))
    ctx = sa.SEALContext(parms, True, sa.SEC_LEVEL_TYPE.TC128)
    kg = sa.KeyGenerator(ctx)
    sk = kg.secret_key()
    pk = sa.PublicKey(); kg.create_public_key(pk)
    rk = sa.RelinKeys(); kg.create_relin_keys(rk)
    enc, dec, ev = sa.Encryptor(ctx, pk), sa.Decryptor(ctx, sk), sa.Evaluator(ctx)
    encoder = sa.BatchEncoder(ctx)
    pt = sa.Plaintext(); encoder.encode([3] * 10, pt)
    ct = sa.Ciphertext(); enc.encrypt(pt, ct)
    fresh = dec.invariant_noise_budget(ct)
    depth, budget = 0, fresh
    work = sa.Ciphertext(); enc.encrypt(pt, work)
    while True:
        ev.square_inplace(work)
        ev.relinearize_inplace(work, rk)
        b = dec.invariant_noise_budget(work)
        if b <= 0:
            break
        depth, budget = depth + 1, b
    return {
        "N": n,
        "coeff_modulus_bits": "+".join(str(m.bit_count()) for m in chain),
        "coeff_modulus_total_bits": sum(m.bit_count() for m in chain),
        "plain_modulus": PLAIN_MODULUS,
        "slots": encoder.slot_count(),
        "security_bits_classical": 128,
        "fresh_noise_budget_bits": fresh,
        "mult_depth_with_relin": depth,
        "noise_budget_after_last_ok_mult": budget,
    }


def tenseal_sizes(n):
    ctx = ts.context(ts.SCHEME_TYPE.BFV, poly_modulus_degree=n, plain_modulus=PLAIN_MODULUS)
    ctx.generate_galois_keys(); ctx.generate_relin_keys()
    keys = {
        "public_key_bytes": len(ctx.serialize(save_public_key=True, save_secret_key=False, save_galois_keys=False, save_relin_keys=False)),
        "secret_key_bytes": len(ctx.serialize(save_public_key=False, save_secret_key=True, save_galois_keys=False, save_relin_keys=False)),
        "relin_keys_bytes": len(ctx.serialize(save_public_key=False, save_secret_key=False, save_galois_keys=False, save_relin_keys=True)),
        "galois_keys_bytes": len(ctx.serialize(save_public_key=False, save_secret_key=False, save_galois_keys=True, save_relin_keys=False)),
    }
    rows = []
    for k in K_RANGE:
        readings = [1234 + i for i in range(k)]
        t0 = time.perf_counter(); v = ts.bfv_vector(ctx, readings); t_enc = time.perf_counter() - t0
        raw = v.serialize()
        b64 = base64.b64encode(raw).decode()
        payload = {"node_id": 0, "battery_level": 95, "batch_HMAC": ["0" * 64] * k,
                   "batch_timestamps": [1700000000.0 + i for i in range(k)], "enc_biometrics": b64, "batch_size": k}
        mqtt = len(compress_data(payload).encode())
        t0 = time.perf_counter(); ts.bfv_vector_from(ctx, raw).decrypt(); t_dec = time.perf_counter() - t0
        rows.append({"N": n, "k": k, "ciphertext_raw_bytes": len(raw), "ciphertext_b64_bytes": len(b64),
                     "mqtt_payload_bytes": mqtt, "plaintext_bytes_8k": 8 * k,
                     "expansion_ratio_raw": round(len(raw) / (8 * k), 1),
                     "payload_bytes_per_reading": round(mqtt / k), "encrypt_ms": round(t_enc * 1e3, 2), "decrypt_ms": round(t_dec * 1e3, 2)})
    return keys, rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    params, sizes = [], []
    for n in (4096, 8192):
        p = seal_profile(n)
        keys, rows = tenseal_sizes(n)
        p.update(keys)
        params.append(p); sizes.extend(rows)
    for name, data in (("bfv_params.csv", params), ("bfv_sizes.csv", sizes)):
        with (OUT / name).open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(data[0])); w.writeheader(); w.writerows(data)
    for p in params:
        print(" ".join(f"{k}={v}" for k, v in p.items()))
    for r in sizes:
        if r["k"] in (1, 5, 10):
            print(" ".join(f"{k}={v}" for k, v in r.items()))
    assert all(r["ciphertext_raw_bytes"] <= sizes[0]["ciphertext_raw_bytes"] * 1.01 for r in sizes if r["N"] == 4096), "ct size should not grow with k"


if __name__ == "__main__":
    main()
