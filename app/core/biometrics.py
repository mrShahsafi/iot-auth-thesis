import random
from settings import NUM_NODES


def generate_biometric_vector(biometric_type="fingerprint", nodes_number=None):

    _nodes_number = nodes_number or NUM_NODES

    if biometric_type == "fingerprint":
        trusted_database = {i: random.uniform(0.0, 1.0) for i in range(_nodes_number)}
    else:
        trusted_database = {i: i * 1000 + 1234 for i in range(NUM_NODES)}

    return trusted_database
