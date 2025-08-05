import os
import random

from skimage.feature import hog
from skimage import io, color
import numpy as np

from settings import NUM_NODES,F_P_DIR

def load_fingerprint_vectors(dataset_dir=None):
    dataset_dir = dataset_dir or F_P_DIR
    print(f"loading fingerprint Dataset from : {dataset_dir}.")
    vectors = {}
    for i, fname in enumerate(sorted(os.listdir(dataset_dir))):
        img = io.imread(os.path.join(dataset_dir, fname))
        if img.ndim == 3:
            img = color.rgb2gray(img)
        features, _ = hog(
            img, orientations=9, pixels_per_cell=(8, 8),cells_per_block=(1, 1), visualize=True, feature_vector=True
        )
        vectors[i] = features[:12]  # or :81 based on your setup
    return vectors


def generate_biometric_vector(biometric_type="fingerprint", nodes_number=None,env="real"):
    _nodes_number = nodes_number or NUM_NODES
    if biometric_type == "fingerprint":
        if not env == "real":
            trusted_database = {i: random.randint(1000, 9999) for i in range(NUM_NODES)}
        else:
            _vectors = load_fingerprint_vectors()
            trusted_database = _vectors
    else:
        trusted_database = {i: i * 1000 + 1234 for i in range(NUM_NODES)}

    return trusted_database
