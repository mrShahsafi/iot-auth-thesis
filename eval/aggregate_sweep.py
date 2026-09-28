"""Aggregate the X4 sweep logs into the paper's tables (C17, C18, C19).

    venv/bin/python3 eval/aggregate_sweep.py   -> output/revision/table_batch.csv, table_scale.csv, latency_decomposition.csv,
                                                 security_online.csv (and a Markdown print-out)
"""
import glob
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "output" / "revision" / "logs"
OUT = ROOT / "output" / "revision"
NAME = re.compile(r"metrics_log_(?P<mode>\w+?)_(?P<nodes>\d+)_(?P<msgs>\d+)_(?P<epb>[\d.]+)_(?P<k>\d+)_(?P<batt>\d+)_(?P<N>\d+)_(?P<run>\d+)\.csv")


def load():
    frames = []
    for f in glob.glob(str(LOGS / "metrics_log_*.csv")):
        m = NAME.search(f)
        df = pd.read_csv(f)
        for key in ("mode", "nodes", "K", "N", "run"):
            df[key] = m.group(key) if key == "mode" else int(m.group("k" if key == "K" else key))
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def ci95(x):
    x = np.asarray(x, float)
    return 1.96 * x.std(ddof=1) / np.sqrt(len(x)) if len(x) > 1 else 0.0


def per_run(df):
    """One row per (mode, nodes, k, run): totals over the run."""
    ok = df[(df.replay == 0) & (df.light == 0)]
    g = ok.groupby(["mode", "nodes", "K", "run"])
    out = g.agg(transactions=("bytes", "size"), total_energy_mJ=("energy", "sum"), readings=("k", "sum"),
                mean_latency_ms=("latency_ms", "mean"), max_latency_ms=("latency_ms", "max"), mean_decision_ms=("decision_ms", "mean"),
                bytes_per_msg=("bytes", "mean"), genuine=("genuine", "sum"), genuine_acc=("genuine_accepted", "sum"),
                impostor=("impostor", "sum"), impostor_acc=("impostor_accepted", "sum"), hmac_failed=("hmac_failed", "sum")).reset_index()
    rep = df[df.replay == 1].groupby(["mode", "nodes", "K", "run"]).size().rename("replays_rejected").reset_index()
    return out.merge(rep, how="left").fillna({"replays_rejected": 0})


def main():
    df = load()
    runs = per_run(df)
    ok = df[(df.replay == 0) & (df.light == 0)]

    # Table 4: 10-node Hybrid, k = 1..10, mean ± 95 % CI over runs
    h10 = runs[(runs["mode"] == "Hybrid") & (runs.nodes == 10)]
    rows = []
    for k, g in h10.groupby("K"):
        tx = ok[(ok["mode"] == "Hybrid") & (ok.nodes == 10) & (ok.K == k)]
        lat, acked = tx.latency_ms, tx[tx.decision_ms >= 0]
        e1 = h10[h10.K == 1].total_energy_mJ.mean()
        rows.append({"k": k, "runs": len(g), "transactions": g.transactions.mean(), "readings": g.readings.mean(),
                     "total_energy_J": g.total_energy_mJ.mean() / 1e3, "total_energy_ci_J": ci95(g.total_energy_mJ) / 1e3,
                     "energy_per_reading_mJ": (g.total_energy_mJ / g.readings).mean(),
                     "reduction_vs_k1_pct": 100 * (1 - g.total_energy_mJ.mean() / e1),
                     "mean_latency_ms": lat.mean(), "latency_ci_ms": ci95(lat), "latency_sd_ms": lat.std(ddof=1),
                     "max_latency_ms": lat.max(), "bytes_per_msg": g.bytes_per_msg.mean(),
                     "min_latency_ms": lat.min(), "battery_mean_pct": tx.battery.mean(),
                     "energy_per_tx_mJ": tx.energy.mean(), "energy_per_tx_sd_mJ": tx.energy.std(ddof=1),
                     "mean_decision_ms": acked.decision_ms.mean(), "decision_ci_ms": ci95(acked.decision_ms),
                     "decision_bytes": tx.decision_bytes.mean(), "ack_bytes": tx.ack_bytes.mean(),
                     "unacked": int((tx.decision_ms < 0).sum())})
    t4 = pd.DataFrame(rows).round(2)
    t4.to_csv(OUT / "table_batch.csv", index=False)

    # latency decomposition per k (10 nodes)
    h = ok[(ok["mode"] == "Hybrid") & (ok.nodes == 10) & (ok.decision_ms >= 0)]
    dec = h.groupby("K")[["wait_ms", "enc_ms", "transport_ms", "dec_ms", "match_ms", "latency_ms", "decision_ms"]].mean()
    dec["return_ms"] = dec.decision_ms - dec.latency_ms  # gateway decrypt + match + signed decision back to the node
    dec = dec.round(2)
    dec.to_csv(OUT / "latency_decomposition.csv")

    # Table 6: scalability 10 vs 50 nodes at k = 1 and 10 (run 1 for 50 nodes; mean over runs for 10)
    sc = runs[(runs["mode"] == "Hybrid") & (runs.K.isin([1, 10]))].groupby(["nodes", "K"]).agg(
        total_energy_J=("total_energy_mJ", lambda x: x.mean() / 1e3), mean_latency_ms=("mean_latency_ms", "mean"),
        transactions=("transactions", "mean")).reset_index()
    sc["reduction_vs_k1_pct"] = sc.apply(lambda r: 100 * (1 - r.total_energy_J / sc[(sc.nodes == r.nodes) & (sc.K == 1)].total_energy_J.iloc[0]), axis=1)
    sc = sc.round(2); sc.to_csv(OUT / "table_scale.csv", index=False)

    # Plain baseline vs Hybrid k = 1
    pl = runs[runs["mode"] == "Plain"]
    base = pd.DataFrame([{"mode": "Plain (unbatched, uncompressed)", "bytes_per_msg": pl.bytes_per_msg.mean(), "total_energy_J": pl.total_energy_mJ.mean() / 1e3, "mean_latency_ms": pl.mean_latency_ms.mean(), "mean_decision_ms": pl.mean_decision_ms.mean()},
                         {"mode": "Hybrid k = 1", "bytes_per_msg": h10[h10.K == 1].bytes_per_msg.mean(), "total_energy_J": h10[h10.K == 1].total_energy_mJ.mean() / 1e3, "mean_latency_ms": h10[h10.K == 1].mean_latency_ms.mean(), "mean_decision_ms": h10[h10.K == 1].mean_decision_ms.mean()}]).round(2)
    base.to_csv(OUT / "table_baseline.csv", index=False)

    # security / accuracy online (all Hybrid runs)
    hy = runs[runs["mode"] == "Hybrid"]
    sec = {"genuine_trials": int(hy.genuine.sum()), "FRR_online_pct": round(100 * (1 - hy.genuine_acc.sum() / hy.genuine.sum()), 2),
           "impostor_trials": int(hy.impostor.sum()), "FAR_online_pct": round(100 * hy.impostor_acc.sum() / hy.impostor.sum(), 2),
           "hmac_failures": int(hy.hmac_failed.sum()), "replays_injected_and_rejected": int(hy.replays_rejected.sum()),
           # an accepted replay would show up as a transaction beyond nodes * ceil(15 / k)
           "replays_accepted": int((hy.transactions - hy.nodes * np.ceil(15 / hy.K)).clip(lower=0).sum()),
           "unacknowledged": int((ok[ok["mode"] == "Hybrid"].decision_ms < 0).sum())}
    pd.DataFrame([sec]).to_csv(OUT / "security_online.csv", index=False)

    for name, t in (("Table 4 (10 nodes)", t4), ("Latency decomposition", dec.reset_index()), ("Table 6 (scalability)", sc), ("Baseline", base), ("Security", pd.DataFrame([sec]))):
        print(f"\n## {name}\n" + t.to_string(index=False))


if __name__ == "__main__":
    main()
