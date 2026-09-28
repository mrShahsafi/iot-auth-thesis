"""X5: leakage-aware regression analysis (C20).

    venv/bin/python3 eval/ml_eval.py   -> output/revision/ml_metrics.csv, ml_ablation.csv, ml_importance.csv

GroupKFold(5) by node_id on the 10-node Hybrid sweep; targets latency_ms, energy per reading (mJ) and the
cost index; models RF, XGBoost, MLP and an analytic baseline; MAE / RMSE / R2 as mean ± sd over folds.
"""
import glob
import re
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "output" / "revision" / "logs"
OUT = ROOT / "output" / "revision"
EPB = 0.001  # mJ per byte, settings.ENERGY_PER_BYTE
INTERARRIVAL_MS = 1250.0  # mean of U(0.5, 2) s between readings in hybrid.py


def load():
    frames = []
    for f in glob.glob(str(LOGS / "metrics_log_Hybrid_10_*_4096_*.csv")):
        df = pd.read_csv(f)
        df["run"] = int(re.search(r"_(\d+)\.csv$", f).group(1))
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    df = df[(df.replay == 0) & (df.light == 0)].copy()
    df["energy_per_reading"] = df.energy / df.k
    df["cost_index"] = 0.5 * df.latency_ms / df.latency_ms.max() + 0.5 * df.energy_per_reading / df.energy_per_reading.max()
    return df


def models():
    return {
        "Random Forest": lambda: RandomForestRegressor(n_estimators=200, random_state=0),
        "XGBoost": lambda: XGBRegressor(n_estimators=200, max_depth=4, learning_rate=0.1, random_state=0, verbosity=0),
        "MLP": lambda: make_pipeline(StandardScaler(), MLPRegressor(hidden_layer_sizes=(128, 64), max_iter=2000, random_state=0)),
    }


def baseline(target, X, df_test):
    if target == "energy_per_reading":
        return (df_test.bytes.values + df_test.ack_bytes.values) * EPB / df_test.k.values  # request + ack
    if target == "latency_ms":
        return (df_test.k.values - 1) * INTERARRIVAL_MS + 30.0
    lat = (df_test.k.values - 1) * INTERARRIVAL_MS + 30.0
    epr = (df_test.bytes.values + df_test.ack_bytes.values) * EPB / df_test.k.values
    return 0.5 * lat / LAT_MAX + 0.5 * epr / EPR_MAX


def evaluate(df, features, tag):
    X, groups = df[features].values, df.node_id.values
    rows = []
    for target in ("latency_ms", "energy_per_reading", "cost_index"):
        y = df[target].values
        scores = {name: [] for name in list(models()) + ["Analytic baseline"]}
        for tr, te in GroupKFold(5).split(X, y, groups):
            for name, make in models().items():
                m = make().fit(X[tr], y[tr]); p = m.predict(X[te])
                scores[name].append((mean_absolute_error(y[te], p), np.sqrt(mean_squared_error(y[te], p)), r2_score(y[te], p)))
            p = baseline(target, None, df.iloc[te])
            scores["Analytic baseline"].append((mean_absolute_error(y[te], p), np.sqrt(mean_squared_error(y[te], p)), r2_score(y[te], p)))
        for name, s in scores.items():
            s = np.array(s)
            rows.append({"features": tag, "target": target, "model": name,
                         "MAE": s[:, 0].mean(), "MAE_sd": s[:, 0].std(), "RMSE": s[:, 1].mean(), "RMSE_sd": s[:, 1].std(),
                         "R2": s[:, 2].mean(), "R2_sd": s[:, 2].std()})
    return pd.DataFrame(rows)


def extrapolate(df, features, k_max=8):
    """Train on transactions with k <= k_max, test on the unseen k > k_max (R1.7: generalization beyond the sampled k)."""
    tr, te = df[df.k <= k_max], df[df.k > k_max]
    rows = []
    for target in ("latency_ms", "energy_per_reading", "cost_index"):
        preds = {name: make().fit(tr[features].values, tr[target].values).predict(te[features].values) for name, make in models().items()}
        preds["Analytic baseline"] = baseline(target, None, te)
        y = te[target].values
        for name, p in preds.items():
            rows.append({"target": target, "model": name, "train": f"k <= {k_max} ({len(tr)})", "test": f"k > {k_max} ({len(te)})",
                         "MAE": mean_absolute_error(y, p), "RMSE": np.sqrt(mean_squared_error(y, p)), "R2": r2_score(y, p)})
    return pd.DataFrame(rows)


def main():
    global LAT_MAX, EPR_MAX
    df = load()
    LAT_MAX, EPR_MAX = df.latency_ms.max(), df.energy_per_reading.max()
    full = ["k", "bytes", "battery"]
    metrics = evaluate(df, full, "k+bytes+battery").round(4)
    metrics.to_csv(OUT / "ml_metrics.csv", index=False)
    extrapolate(df, full).round(4).to_csv(OUT / "ml_extrapolation.csv", index=False)
    abl = pd.concat([evaluate(df, ["bytes", "battery"], "no k"), evaluate(df, ["k", "battery"], "no bytes"), evaluate(df, ["k"], "k only")]).round(4)
    abl = abl[abl.model == "Random Forest"]
    abl.to_csv(OUT / "ml_ablation.csv", index=False)
    imps = []
    for target in ("latency_ms", "energy_per_reading", "cost_index"):
        rf = RandomForestRegressor(n_estimators=200, random_state=0).fit(df[full].values, df[target].values)
        imp = permutation_importance(rf, df[full].values, df[target].values, n_repeats=20, random_state=0)
        imps.append(pd.DataFrame({"target": target, "feature": full, "permutation_importance": imp.importances_mean.round(4), "sd": imp.importances_std.round(4)}))
    pd.concat(imps).to_csv(OUT / "ml_importance.csv", index=False)
    print(f"rows={len(df)} nodes={df.node_id.nunique()} runs={df.run.nunique()}")
    print(metrics.to_string(index=False)); print(abl.to_string(index=False))


if __name__ == "__main__":
    main()
