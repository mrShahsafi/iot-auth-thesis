"""X3: FAR / FRR / EER of the fingerprint pipeline (C13, C19).

    venv/bin/python3 eval/biometric_eer.py --subjects 3      # pilot
    venv/bin/python3 eval/biometric_eer.py                   # all 10 subjects -> output/revision/eer.csv, eer_scores.csv

Features: HOG exactly as app/core/biometrics.py (9 orientations, 8x8 cells, 1x1 blocks), truncated to the
first d components (the code uses d = 12), then quantized as in D2: x_int = clip(round(s * x), 0, s), s = 256.
Score: squared Euclidean distance; genuine = same subject, impostor = different subjects, all image pairs.
EER uncertainty: bootstrap over pairs (B = 1000).
"""
import argparse
import csv
import itertools
import re
from pathlib import Path

import numpy as np
from skimage import color, io
from skimage.feature import hog

ROOT = Path(__file__).resolve().parents[1]
FP_DIR = ROOT / "settings" / "fingerprints"
OUT = ROOT / "output" / "revision"
S = 256
DIMS = (12, 64, 128, 512, None)  # None = full descriptor


def features():
    subj, feats = [], []
    for f in sorted(FP_DIR.iterdir()):
        m = re.match(r"(\d+)_(\d+)\.tif", f.name)
        if not m:
            continue
        img = io.imread(f)
        if img.ndim == 3:
            img = color.rgb2gray(img)
        h = hog(img, orientations=9, pixels_per_cell=(8, 8), cells_per_block=(1, 1), feature_vector=True)
        subj.append(int(m.group(1))); feats.append(h)
    return np.array(subj), np.array(feats)


def scores(X, subj):
    i, j = np.triu_indices(len(X), 1)
    d2 = ((X[i] - X[j]) ** 2).sum(1)
    return d2[subj[i] == subj[j]], d2[subj[i] != subj[j]]


def eer(gen, imp):
    ths = np.unique(np.concatenate([gen, imp]))
    frr = np.array([(gen > t).mean() for t in ths])   # genuine rejected when distance > threshold
    far = np.array([(imp <= t).mean() for t in ths])  # impostor accepted when distance <= threshold
    k = np.argmin(np.abs(far - frr))
    far1 = frr[np.argmax(far <= 0.01)] if (far <= 0.01).any() else np.nan  # FRR at FAR <= 1 %
    return (far[k] + frr[k]) / 2, ths[k], far[k], frr[k], far1


def bootstrap_eer(gen, imp, B=1000, seed=0):
    rng = np.random.default_rng(seed)
    vals = [eer(rng.choice(gen, len(gen)), rng.choice(imp, len(imp)))[0] for _ in range(B)]
    return np.mean(vals), np.std(vals)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--subjects", type=int, default=10); a = ap.parse_args()
    subj, F = features()
    keep = np.isin(subj, np.unique(subj)[: a.subjects]); subj, F = subj[keep], F[keep]
    rows, score_rows = [], []
    variants = [(f"first_{d}" if d else "full", F if d is None else F[:, :d]) for d in DIMS]
    cells = F.reshape(len(F), 37, 37, 9)  # 300 px / 8 px cells -> 37 x 37 cells x 9 orientations
    for g in (2, 3, 4):
        edges = np.linspace(0, 37, g + 1).astype(int)
        pooled = np.stack([cells[:, edges[a]:edges[a + 1], edges[b]:edges[b + 1], :].mean((1, 2))
                           for a in range(g) for b in range(g)], 1).reshape(len(F), -1)
        variants.append((f"pooled_{g}x{g}", pooled))
    for name, Xf in variants:
        d = Xf.shape[1]
        s = min(S, int(np.sqrt((1032193 - 1) / d)))  # keep d * s^2 < t so the BFV score cannot wrap
        for kind, X in (("float", Xf), (f"quantized_s{s}", np.clip(np.rint(s * Xf), 0, s))):
            gen, imp = scores(X, subj)
            e, th, far, frr, frr_at_far1 = eer(gen, imp)
            m, sd = bootstrap_eer(gen, imp)
            rows.append({"subjects": a.subjects, "images": len(X), "feature": name, "d": d, "encoding": kind,
                         "genuine_pairs": len(gen), "impostor_pairs": len(imp),
                         "EER": round(e, 4), "EER_boot_mean": round(m, 4), "EER_boot_sd": round(sd, 4),
                         "threshold_at_EER": round(float(th), 3), "FAR_at_EER": round(far, 4), "FRR_at_EER": round(frr, 4),
                         "FRR_at_FAR_1pct": None if np.isnan(frr_at_far1) else round(frr_at_far1, 4),
                         "genuine_mean": round(gen.mean(), 3), "impostor_mean": round(imp.mean(), 3)})
            if kind.startswith("quantized") and a.subjects == 10:
                score_rows += [{"feature": name, "d": d, "type": "genuine", "score": float(v)} for v in gen]
                score_rows += [{"feature": name, "d": d, "type": "impostor", "score": float(v)} for v in imp]
    for r in rows:
        print(" ".join(f"{k}={v}" for k, v in r.items()))
    if a.subjects == 10:
        OUT.mkdir(parents=True, exist_ok=True)
        with (OUT / "eer.csv").open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
        with (OUT / "eer_scores.csv").open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(score_rows[0])); w.writeheader(); w.writerows(score_rows)
    assert all(r["genuine_pairs"] == a.subjects * 28 for r in rows)


if __name__ == "__main__":
    main()
