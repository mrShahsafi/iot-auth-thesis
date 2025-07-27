import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

from settings import OUTPUT_FILE, MODE, OUTPUT_DIR, LOG_CSV

from .quadratic_regressoin import combined_cost

def plot_energy_consumption(nodes, energy_values):
    plt.figure(figsize=(8, 4))
    plt.bar(nodes, energy_values, color="purple")
    plt.xlabel("Node ID")
    plt.ylabel("Energy Consumed (mJ)")
    plt.title("Energy Consumption per Node - Adaptive Batching & Crypto")
    plt.grid(axis="y")
    plt.tight_layout()
    plt.show()


def plot_boxplot_latency(mode=None):
    _mode = mode or MODE
    _file = LOG_CSV
    df = pd.read_csv(_file)
    plt.figure(figsize=(8, 4))
    df.boxplot(column="latency_ms", by="node_id")
    plt.ylabel("Latency (ms)")
    plt.title("Boxplot Latency per Node")
    plt.suptitle("")
    plt.show()


def plot_latency_energy_vs_batch_size(batch_sizes, latencies=None, energies=None, alpha=1.0):
    # Fit polynomials
    latency_coeffs = np.polyfit(batch_sizes, latencies, deg=2)
    energy_coeffs = np.polyfit(batch_sizes, energies, deg=2)

    # Evaluate combined cost
    combined_costs = [combined_cost(lat, en, alpha) for lat, en in zip(latencies, energies)]

    # Compute optimal batch sizes (analytically)
    optimal_latency_batch = round(-latency_coeffs[1] / (2 * latency_coeffs[0]))
    optimal_latency = np.polyval(latency_coeffs, optimal_latency_batch)

    optimal_energy_batch = round(-energy_coeffs[1] / (2 * energy_coeffs[0]))
    optimal_energy = np.polyval(energy_coeffs, optimal_energy_batch)
    
    if optimal_latency_batch < 0:
        optimal_latency_batch = 0
    
    # ---- 2D Plot ----
    fig1 = plt.figure(figsize=(10, 6))
    plt.plot(batch_sizes, latencies, marker='o', label='Latency (ms)', color='blue')
    plt.plot(batch_sizes, energies, marker='s', label='Energy (mJ)', color='purple')
    plt.plot(batch_sizes, combined_costs, marker='^', label='Combined Cost', color='green')

    # Show optimal points
    plt.axvline(x=optimal_latency_batch, color='blue', linestyle='--', label=f'Opt Latency: {optimal_latency_batch}')
    plt.axvline(x=optimal_energy_batch, color='purple', linestyle='--', label=f'Opt Energy: {optimal_energy_batch}')
    plt.scatter([optimal_latency_batch], [optimal_latency], color='blue', s=80)
    plt.scatter([optimal_energy_batch], [optimal_energy], color='purple', s=80)

    plt.title("Latency, Energy, and Combined Cost vs Batch Size")
    plt.xlabel("Batch Size")
    plt.ylabel("Value")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    # ---- 3D Plot ----
    fig2 = plt.figure(figsize=(10, 7))
    ax = fig2.add_subplot(111, projection='3d')
    ax.plot(batch_sizes, latencies, zs=0, zdir='z', label='Latency', color='blue', marker='o')
    ax.plot(batch_sizes, energies, zs=0, zdir='y', label='Energy', color='green', marker='^')

    ax.set_xlabel('Batch Size')
    ax.set_ylabel('Latency (ms)')
    ax.set_zlabel('Energy (mJ)')
    ax.set_title('3D Plot: Latency and Energy vs Batch Size')
    ax.legend()
    plt.tight_layout()
    plt.show()

    fig2 = plt.figure(figsize=(10, 7))
    ax = fig2.add_subplot(111, projection='3d')
    ax.plot(batch_sizes, latencies, zs=0, zdir='z', label='Latency', color='blue', marker='o')
    ax.plot(batch_sizes, energies, zs=0, zdir='y', label='Energy', color='green', marker='^')

    ax.set_xlabel('Batch Size')
    ax.set_ylabel('Latency (ms)')
    ax.set_zlabel('Energy (mJ)')
    ax.set_title('3D Plot of Latency and Energy vs Batch Size')
    ax.legend()
    
    plt.show()