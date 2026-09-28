import os
import re

import numpy as np
from skimage import color, io
from skimage.feature import hog

from settings import NUM_NODES, F_P_DIR, FEATURE_POOL, QUANT_SCALE


def pooled_hog(img, g=None):
    """g x g spatially pooled HOG (9 orientations, 8 px cells), quantized to integers in [0, QUANT_SCALE]."""
    g = g or FEATURE_POOL
    if img.ndim == 3:
        img = color.rgb2gray(img)
    cells = hog(img, orientations=9, pixels_per_cell=(8, 8), cells_per_block=(1, 1), feature_vector=False)
    cells = cells.reshape(cells.shape[0], cells.shape[1], 9)
    ye = np.linspace(0, cells.shape[0], g + 1).astype(int)
    xe = np.linspace(0, cells.shape[1], g + 1).astype(int)
    pooled = np.concatenate([cells[ye[a]:ye[a + 1], xe[b]:xe[b + 1]].mean((0, 1)) for a in range(g) for b in range(g)])
    return np.clip(np.rint(QUANT_SCALE * pooled), 0, QUANT_SCALE).astype(int).tolist()


def load_fingerprint_vectors(dataset_dir=None):
    """subject id -> list of quantized feature vectors, one per impression, in file order."""
    dataset_dir = dataset_dir or F_P_DIR
    print(f"loading fingerprint Dataset from : {dataset_dir}.")
    subjects = {}
    for fname in sorted(os.listdir(dataset_dir)):
        m = re.match(r"(\d+)_(\d+)\.tif$", fname)
        if m:
            subjects.setdefault(int(m.group(1)), []).append(pooled_hog(io.imread(os.path.join(dataset_dir, fname))))
    return subjects


def generate_biometric_vector(nodes_number=None):
    """Per node: enrolled template (impression 1), genuine probes (other impressions), impostor probes (other subjects).
    Nodes beyond the number of subjects reuse subjects round-robin."""
    subjects = load_fingerprint_vectors()
    ids = sorted(subjects)
    db = {}
    for node in range(nodes_number or NUM_NODES):
        sid = ids[node % len(ids)]
        impressions = subjects[sid]
        db[node] = {
            "subject": sid,
            "template": impressions[0],
            "genuine": impressions[1:],
            "impostor": [v for s in ids if s != sid for v in subjects[s]],
        }
    return db
