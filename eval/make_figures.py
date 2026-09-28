"""Figures 2-8 of the revised paper from the X4/X5 outputs (C28).

    venv/bin/python3 eval/make_figures.py   -> output/revision/figures/fig2.png ... fig8.png, output/revision/correlation.csv

Each figure is drawn at its printed size (one 3.23 in column of the two-column A4 layout) with 8 pt Times New Roman,
so text prints at true size. Colors: blue series slot, recessive grid, blue-red diverging map with a gray midpoint.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

ROOT = Path(__file__).resolve().parents[1]
REV = ROOT / "output" / "revision"
OUT = REV / "figures"
COL_W = 3.23  # inches, one column
BLUE, INK, INK2, GRID = "#2a78d6", "#0b0b0b", "#52514e", "#e4e3df"
DIVERGING = LinearSegmentedColormap.from_list("blue_gray_red", ["#184f95", "#6da7ec", "#f0efec", "#ec8a7f", "#b8322f"])

plt.rcParams.update({
    "font.family": "Times New Roman", "font.size": 8, "axes.labelsize": 8, "xtick.labelsize": 7.5, "ytick.labelsize": 7.5,
    "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
    "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": 0.6, "xtick.major.width": 0.6,
    "ytick.major.width": 0.6, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.5, "axes.axisbelow": True,
    "savefig.dpi": 300, "savefig.facecolor": "white", "figure.facecolor": "white",
})


def save(fig, name):
    fig.savefig(OUT / name)
    plt.close(fig)


def bars(ax, x, y, **kw):
    ax.bar(x, y, width=0.7, color=BLUE, edgecolor="white", linewidth=0.8, **kw)


def flow(tb):
    """Protocol flow (C08): numbered steps on Node / Broker / Gateway lifelines; message sizes from the sweep."""
    req_kb = tb.bytes_per_msg.mean() / 1e3
    dec_lo, dec_hi, ack_b = tb.decision_bytes.min(), tb.decision_bytes.max(), tb.ack_bytes.mean()
    fig, ax = plt.subplots(figsize=(COL_W, 3.9))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    X = {"Node": 0.14, "Broker": 0.5, "Gateway": 0.86}
    for name, x in X.items():
        ax.text(x, 0.975, name, ha="center", va="center", fontsize=8, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=INK2, lw=0.6))
        ax.plot([x, x], [0.04, 0.945], color=GRID, lw=1.2, zorder=0)

    def num(x, y, n):
        ax.text(x, y, str(n), ha="center", va="center", fontsize=6.5, color="white", fontweight="bold",
                bbox=dict(boxstyle="circle,pad=0.18", fc=BLUE, ec="none"))

    def note(side, y, n, text):
        x = X[side]
        ha = "left" if side == "Node" else "right"
        num(x, y, n)
        ax.text(x + (0.045 if ha == "left" else -0.045), y, text, ha=ha, va="center", fontsize=6.3, color=INK, linespacing=1.15)

    def msg(a, b, y, label, n=None, dashed=False):
        ax.annotate("", xy=(X[b], y), xytext=(X[a], y),
                    arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.9, ls="--" if dashed else "-", shrinkA=0, shrinkB=0))
        mid = (X[a] + X[b]) / 2
        ax.text(mid, y + 0.018, label, ha="center", va="bottom", fontsize=6, color=INK2)
        if n:
            num(mid, y - 0.024, n)

    note("Node", 0.89, 1, "Capture k readings:\nHOG, 2 × 2 pooling,\nquantize (d = 36, s = 169)")
    note("Node", 0.79, 2, "Pack k · 36 values;\nBFV-encrypt with pk")
    note("Node", 0.715, 3, "HMAC-SHA256 tag and\ntimestamp per reading")
    msg("Node", "Broker", 0.64, f"Message 1: request, {req_kb:.0f} kB", 4)
    msg("Broker", "Gateway", 0.555, "forwarded; broker sees\nciphertext and tags only", 5)
    note("Gateway", 0.475, 6, "Freshness check:\nwindow Δ = 60 s, seen set;\nreplays rejected here")
    note("Gateway", 0.38, 7, "Decrypt with sk; verify\neach tag; D(x, y) ≤ τ ?")
    msg("Gateway", "Broker", 0.255, f"Message 2: decision,\n{dec_lo:.0f} to {dec_hi:.0f} B", 8)
    msg("Broker", "Node", 0.205, "")
    note("Node", 0.155, 9, "Verify decision tag;\nsigned acknowledgement")
    msg("Node", "Broker", 0.075, f"Message 3: ack, {ack_b:.0f} B")
    msg("Broker", "Gateway", 0.04, "")
    fig.subplots_adjust(0, 0, 1, 1)
    save(fig, "fig_flow.png")


def scores():
    """Genuine vs impostor squared-distance scores (R3.5): transmitted pooled HOG vs the original first-12 feature."""
    sc = pd.read_csv(REV / "eer_scores.csv")
    eer = pd.read_csv(REV / "eer.csv")
    ORANGE = "#eb6834"
    fig, axes = plt.subplots(1, 2, figsize=(COL_W, 2.0), layout="constrained")
    for ax, (feat, title) in zip(axes, (("pooled_2x2", "2 × 2 pooled HOG, d = 36"), ("first_12", "First 12 HOG values"))):
        g = sc[(sc.feature == feat) & (sc.type == "genuine")].score / 1e3
        i = sc[(sc.feature == feat) & (sc.type == "impostor")].score / 1e3
        hi = np.percentile(np.r_[g, i], 99)
        bins = np.linspace(0, hi, 26)
        for x, color, label in ((g, BLUE, "Genuine"), (i, ORANGE, "Impostor")):
            ax.hist(x.clip(upper=hi), bins=bins, weights=np.full(len(x), 100 / len(x)), histtype="step", lw=1.4, color=color, label=label)
        tau = eer[(eer.feature == feat) & (eer.encoding != "float")].threshold_at_EER.iloc[0] / 1e3
        ax.axvline(tau, color=INK2, lw=0.9, ls="--")
        ax.text(tau, ax.get_ylim()[1] * 0.97, " τ", color=INK2, fontsize=7, va="top")
        ax.set_title(title, fontsize=7.5, color=INK)
        ax.set_xlabel("Squared distance (×10³)")
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("Comparisons (% of class)")
    axes[0].legend(frameon=False, fontsize=6.5, loc="upper right")
    save(fig, "fig_scores.png")


def main():
    OUT.mkdir(exist_ok=True)
    tb = pd.read_csv(REV / "table_batch.csv")
    k = tb.k.astype(int)

    # Fig. 2 latency: mean +/- sd, in seconds
    fig, ax = plt.subplots(figsize=(COL_W, 2.2), layout="constrained")
    ax.errorbar(k, tb.mean_latency_ms / 1e3, yerr=tb.latency_sd_ms / 1e3, color=BLUE, lw=1.4, marker="o", ms=4,
                elinewidth=0.8, capsize=2.5, ecolor=INK2)
    ax.set(xlabel="Batch size k", ylabel="Latency to gateway (s)", xticks=k, ylim=(0, None))
    for kk, off, ha in ((1, (-3, 11), "left"), (2, (7, -2), "left"), (10, (0, 7), "center")):
        v = tb.loc[tb.k == kk, "mean_latency_ms"].iloc[0]
        ax.annotate(f"{v:,.0f} ms" if v < 1e3 else f"{v / 1e3:.2f} s", (kk, v / 1e3), xytext=off,
                    textcoords="offset points", ha=ha, va="bottom", fontsize=7, color=INK2)
    save(fig, "fig2.png")

    # Fig. 3 total energy per workload
    fig, ax = plt.subplots(figsize=(COL_W, 2.0), layout="constrained")
    bars(ax, k, tb.total_energy_J)
    for kk, v in zip(k, tb.total_energy_J):
        ax.text(kk, v + 0.25, f"{v:.2f}", ha="center", va="bottom", fontsize=6.5, color=INK2)
    ax.set(xlabel="Batch size k", ylabel="Total energy (J)", xticks=k, ylim=(0, tb.total_energy_J.max() * 1.12))
    ax.grid(axis="x", visible=False)
    save(fig, "fig3.png")

    # Fig. 4 two panels (no dual axis): battery level and transactions
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(COL_W, 1.9), layout="constrained", sharex=True)
    a1.plot(k, tb.battery_mean_pct, color=BLUE, lw=1.4, marker="o", ms=3.5)
    a1.set(xlabel="Batch size k", ylabel="Mean battery level (%)", ylim=(75, 90), xticks=[1, 4, 7, 10])
    bars(a2, k, tb.transactions)
    a2.set(xlabel="Batch size k", ylabel="Transactions (10 nodes)", xticks=[1, 4, 7, 10])
    a2.grid(axis="x", visible=False)
    save(fig, "fig4.png")

    # Fig. 5 Pearson correlation over transactions of the 10-node sweep
    logs = pd.concat(pd.read_csv(f) for f in (REV / "logs").glob("metrics_log_Hybrid_10_*_4096_*.csv"))
    logs = logs[(logs.replay == 0) & (logs.light == 0)].copy()
    epr = logs.energy / logs.k
    logs["cost_index"] = 0.5 * logs.latency_ms / logs.latency_ms.max() + 0.5 * epr / epr.max()  # as in eval/ml_eval.py
    cols = {"latency_ms": "Latency", "bytes": "Bytes", "energy": "Energy", "k": "Batch size k", "cost_index": "Cost index"}
    corr = logs[list(cols)].rename(columns=cols).corr()
    corr.round(3).to_csv(REV / "correlation.csv")
    fig, ax = plt.subplots(figsize=(COL_W, 2.75), layout="constrained")
    im = ax.imshow(corr.values, cmap=DIVERGING, vmin=-1, vmax=1)
    ax.set_xticks(range(len(cols)), corr.columns, rotation=30, ha="right")
    ax.set_yticks(range(len(cols)), corr.columns)
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    for i in range(len(cols)):
        for j in range(len(cols)):
            v = corr.values[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=7, color="white" if abs(v) > 0.6 else INK)
    fig.colorbar(im, ax=ax, shrink=0.85, ticks=[-1, -0.5, 0, 0.5, 1]).outline.set_visible(False)
    save(fig, "fig5.png")

    # Figs. 6-8 permutation importance, one target each
    imp = pd.read_csv(REV / "ml_importance.csv")
    names = {"k": "Batch size k", "bytes": "Transmitted bytes", "battery": "Battery level"}
    for fig_no, target in ((6, "cost_index"), (7, "energy_per_reading"), (8, "latency_ms")):
        t = imp[imp.target == target].set_index("feature").loc[["battery", "bytes", "k"]]
        fig, ax = plt.subplots(figsize=(COL_W, 1.45), layout="constrained")
        ax.barh([names[f] for f in t.index], t.permutation_importance, xerr=t.sd, height=0.6, color=BLUE,
                edgecolor="white", linewidth=0.8, error_kw={"elinewidth": 0.8, "ecolor": INK2, "capsize": 2})
        for y, (v, sd) in enumerate(zip(t.permutation_importance, t.sd)):
            ax.text(v + sd + 0.05, y, f"{v:.2f}", va="center", fontsize=7, color=INK2)
        ax.set(xlabel="Permutation importance (drop in R²)", xlim=(0, 2.3))
        ax.grid(axis="y", visible=False)
        save(fig, f"fig{fig_no}.png")
    flow(tb)
    scores()
    print(corr.round(3).to_string())


if __name__ == "__main__":
    main()
