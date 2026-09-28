"""X2: cost of fully homomorphic squared-distance matching (C10 / Section 4.6 micro-benchmark).

    venv/bin/python3 eval/he_distance_bench.py     -> output/revision/he_match_bench.csv

Two arms, same BFV context as app/core/tenseal.py (N = 4096, t = 1,032,193):
  A  prototype  : gateway decrypts the query, computes ||q - t||^2 in plaintext
  B  homomorphic: gateway computes Enc(||q - t||^2) = sum((Enc(q) - t)^2) on the ciphertext,
                  returns it; the device decrypts the score and applies the threshold.
Readings are integers in [0, S]; S is chosen so that d * S^2 < t (no wrap-around mod t).
"""
import csv
import math
import statistics as st
import sys
import time
from pathlib import Path

import numpy as np
import tenseal as ts

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "revision"
T = 1032193
REPS = 20
DIMS = (12, 64, 128)


def bench(n=4096):
    ctx = ts.context(ts.SCHEME_TYPE.BFV, poly_modulus_degree=n, plain_modulus=T)
    ctx.generate_galois_keys(); ctx.generate_relin_keys()
    rng = np.random.default_rng(0)
    rows = []
    for d in DIMS:
        S = int(math.isqrt((T - 1) // d))  # largest reading value that keeps the score below t
        q = rng.integers(0, S + 1, d).tolist()
        tmpl = rng.integers(0, S + 1, d).tolist()
        expected = sum((a - b) ** 2 for a, b in zip(q, tmpl))
        enc_ms, a_ms, b_ms, dec_ms, ok = [], [], [], [], True
        for _ in range(REPS):
            t0 = time.perf_counter(); enc_q = ts.bfv_vector(ctx, q); enc_ms.append(time.perf_counter() - t0)
            raw = enc_q.serialize()
            # arm A: decrypt then match
            t0 = time.perf_counter()
            qa = np.array(ts.bfv_vector_from(ctx, raw).decrypt()[:d]); score_a = int(((qa - np.array(tmpl)) ** 2).sum())
            a_ms.append(time.perf_counter() - t0)
            # arm B: match on ciphertext, decrypt score on device
            t0 = time.perf_counter()
            diff = ts.bfv_vector_from(ctx, raw) - tmpl
            enc_score = (diff * diff).sum()
            score_raw = enc_score.serialize()
            b_ms.append(time.perf_counter() - t0)
            t0 = time.perf_counter(); score_b = ts.bfv_vector_from(ctx, score_raw).decrypt()[0]; dec_ms.append(time.perf_counter() - t0)
            ok &= (score_a == expected == score_b)
        rows.append({
            "N": n, "d": d, "max_reading_value_S": S, "score_bound_dS2": d * S * S, "plain_modulus": T,
            "query_ct_bytes": len(raw), "score_ct_bytes": len(score_raw),
            "encrypt_ms": round(st.mean(enc_ms) * 1e3, 2),
            "armA_decrypt_and_match_ms": round(st.mean(a_ms) * 1e3, 2), "armA_sd": round(st.stdev(a_ms) * 1e3, 2),
            "armB_homomorphic_match_ms": round(st.mean(b_ms) * 1e3, 2), "armB_sd": round(st.stdev(b_ms) * 1e3, 2),
            "armB_device_decrypt_ms": round(st.mean(dec_ms) * 1e3, 2),
            "armB_extra_downlink_bytes": len(score_raw), "correct": ok,
        })
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = bench()
    with (OUT / "he_match_bench.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    for r in rows:
        print(" ".join(f"{k}={v}" for k, v in r.items()))
    assert all(r["correct"] for r in rows), "homomorphic score must equal plaintext score"


if __name__ == "__main__":
    main()
