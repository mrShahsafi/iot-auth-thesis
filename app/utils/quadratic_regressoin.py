import numpy as np
import matplotlib.pyplot as plt
from numpy.polynomial.polynomial import Polynomial
from mpl_toolkits.mplot3d import Axes3D


# تخمین تأخیر بر اساس مدل درجه دوم
def estimate_latency(batch_size):
    return round(136.34 * batch_size**2 + 308.83 * batch_size + 1102.12, 2)


# تخمین انرژی بر اساس مدل درجه دوم
def estimate_energy(batch_size):
    return round(25.16 * batch_size**2 - 380.18 * batch_size + 1475.66, 2)


# تابع هزینه ترکیبی: latency + alpha * energy
def estimate_combined_cost(batch_size, alpha=1.0):
    return estimate_latency(batch_size) + alpha * estimate_energy(batch_size)


def combined_cost(latency, energy, alpha=1.0):
    return latency + alpha * energy


"""
batch_sizes = np.arange(1, 16)
latencies = [estimate_latency(b) for b in batch_sizes]
energies = [estimate_energy(b) for b in batch_sizes]
combined_costs = [estimate_combined_cost(b, alpha=1.0) for b in batch_sizes]
"""
