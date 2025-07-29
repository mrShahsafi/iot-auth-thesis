import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os

from settings import OUTPUT_FILE, MODE, OUTPUT_DIR, LOG_CSV, NUM_NODES

from .quadratic_regressoin import combined_cost


def plot_energy_consumption(nodes, energy_values):
    plt.figure(figsize=(8, 4))
    plt.bar(nodes, energy_values, color="purple")
    plt.xlabel("Node ID")
    plt.ylabel("Energy Consumed (mJ)")
    plt.title(
        f"Energy Consumption per Node - Adaptive Batching & Crypto (Nodes: {NUM_NODES})"
    )
    plt.grid(axis="y")
    plt.tight_layout()

    # Save figure instead of showing it
    save_path = os.path.join(
        OUTPUT_DIR, f"plots/energy_consumption_nodes_{NUM_NODES}.png"
    )
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path)
    plt.close()


def plot_boxplot_latency(mode=None):
    _mode = mode or MODE
    _file = LOG_CSV
    df = pd.read_csv(_file)
    plt.figure(figsize=(8, 4))
    df.boxplot(column="latency_ms", by="node_id")
    plt.ylabel("Latency (ms)")
    plt.title(f"Boxplot Latency per Node (Nodes: {NUM_NODES})")
    plt.suptitle("")

    # Save figure instead of showing it
    save_path = os.path.join(OUTPUT_DIR, f"plots/latency_boxplot_nodes_{NUM_NODES}.png")
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path)
    plt.close()


# def plot_latency_energy_vs_batch_size(batch_sizes, latencies, energies, alpha=1.0):
#     """
#     Plots latency, energy, and combined cost vs batch size.
#     Auto-detects optimal batch sizes empirically within the data range.
#     """
#
#     # Ensure data is in NumPy format
#     batch_sizes = np.array(batch_sizes)
#     latencies = np.array(latencies)
#     energies = np.array(energies)
#
#     # Combined cost (e.g. weighted latency + energy)
#     combined_costs = latencies + alpha * energies
#
#     # Empirical minima
#     optimal_latency_batch = batch_sizes[np.argmin(latencies)]
#     optimal_latency = latencies[np.argmin(latencies)]
#
#     optimal_energy_batch = batch_sizes[np.argmin(energies)]
#     optimal_energy = energies[np.argmin(energies)]
#
#     optimal_combined_batch = batch_sizes[np.argmin(combined_costs)]
#     optimal_combined_cost = combined_costs[np.argmin(combined_costs)]
#
#     if optimal_latency_batch < 0:
#         optimal_latency_batch = 0
#
#     # ---- 2D Plot ----
#     fig1 = plt.figure(figsize=(10, 6))
#     plt.plot(batch_sizes, latencies, marker="o", label="Latency (ms)", color="blue")
#     plt.plot(batch_sizes, energies, marker="s", label="Energy (mJ)", color="purple")
#     plt.plot(
#         batch_sizes, combined_costs, marker="^", label="Combined Cost", color="green"
#     )
#
#     # Show optimal points
#     plt.axvline(
#         x=optimal_latency_batch,
#         color="blue",
#         linestyle="--",
#         label=f"Opt Latency: {optimal_latency_batch}",
#     )
#     plt.axvline(
#         x=optimal_energy_batch,
#         color="purple",
#         linestyle="--",
#         label=f"Opt Energy: {optimal_energy_batch}",
#     )
#     plt.scatter([optimal_latency_batch], [optimal_latency], color="blue", s=80)
#     plt.scatter([optimal_energy_batch], [optimal_energy], color="purple", s=80)
#
#     plt.title("Latency, Energy, and Combined Cost vs Batch Size")
#     plt.xlabel("Batch Size")
#     plt.ylabel("Value")
#     plt.grid(True)
#     plt.legend()
#     plt.tight_layout()
#
#     # Save figure instead of showing it
#     save_path = os.path.join(
#         OUTPUT_DIR, f"plots/combined_metrics_nodes_{NUM_NODES}.png"
#     )
#     os.makedirs(os.path.dirname(save_path), exist_ok=True)
#     plt.savefig(save_path)
#     plt.close()
#
#     # ---- 3D Plot ----
#     fig2 = plt.figure(figsize=(10, 7))
#     ax = fig2.add_subplot(111, projection="3d")
#     ax.plot(
#         batch_sizes,
#         latencies,
#         zs=0,
#         zdir="z",
#         label="Latency",
#         color="blue",
#         marker="o",
#     )
#     ax.plot(
#         batch_sizes, energies, zs=0, zdir="y", label="Energy", color="green", marker="^"
#     )
#
#     ax.set_xlabel("Batch Size")
#     ax.set_ylabel("Latency (ms)")
#     ax.set_zlabel("Energy (mJ)")
#     ax.set_title("3D Plot: Latency and Energy vs Batch Size")
#     ax.legend()
#     plt.tight_layout()
#
#     # Save figure instead of showing it
#     save_path = os.path.join(OUTPUT_DIR, f"plots/3d_plot1_nodes_{NUM_NODES}.png")
#     os.makedirs(os.path.dirname(save_path), exist_ok=True)
#     plt.savefig(save_path)
#     plt.close()
#
#     fig2 = plt.figure(figsize=(10, 7))
#     ax = fig2.add_subplot(111, projection="3d")
#     ax.plot(
#         batch_sizes,
#         latencies,
#         zs=0,
#         zdir="z",
#         label="Latency",
#         color="blue",
#         marker="o",
#     )
#     ax.plot(
#         batch_sizes, energies, zs=0, zdir="y", label="Energy", color="green", marker="^"
#     )
#
#     ax.set_xlabel("Batch Size")
#     ax.set_ylabel("Latency (ms)")
#     ax.set_zlabel("Energy (mJ)")
#     ax.set_title("3D Plot of Latency and Energy vs Batch Size")
#     ax.legend()
#
#     # Save figure instead of showing it
#     save_path = os.path.join(OUTPUT_DIR, f"plots/3d_plot2_nodes_{NUM_NODES}.png")
#     os.makedirs(os.path.dirname(save_path), exist_ok=True)
#     plt.savefig(save_path)
#     plt.close()


def plot_latency_energy_vs_batch_size(
    batch_sizes, latencies=None, energies=None, alpha=1.0
):
    # Fit polynomials
    latency_coeffs = np.polyfit(batch_sizes, latencies, deg=2)
    energy_coeffs = np.polyfit(batch_sizes, energies, deg=2)

    # Evaluate combined cost
    combined_costs = [
        combined_cost(lat, en, alpha) for lat, en in zip(latencies, energies)
    ]

    # Compute optimal batch sizes (analytically)
    optimal_latency_batch = round(-latency_coeffs[1] / (2 * latency_coeffs[0]))
    optimal_latency = np.polyval(latency_coeffs, optimal_latency_batch)

    optimal_energy_batch = round(-energy_coeffs[1] / (2 * energy_coeffs[0]))
    optimal_energy = np.polyval(energy_coeffs, optimal_energy_batch)

    if optimal_latency_batch < 0:
        optimal_latency_batch = 0

    # ---- 2D Plot ----
    fig1 = plt.figure(figsize=(10, 6))
    plt.plot(batch_sizes, latencies, marker="o", label="Latency (ms)", color="blue")
    plt.plot(batch_sizes, energies, marker="s", label="Energy (mJ)", color="purple")
    plt.plot(
        batch_sizes, combined_costs, marker="^", label="Combined Cost", color="green"
    )

    # Show optimal points
    plt.axvline(
        x=optimal_latency_batch,
        color="blue",
        linestyle="--",
        label=f"Opt Latency: {optimal_latency_batch}",
    )
    plt.axvline(
        x=optimal_energy_batch,
        color="purple",
        linestyle="--",
        label=f"Opt Energy: {optimal_energy_batch}",
    )
    plt.scatter([optimal_latency_batch], [optimal_latency], color="blue", s=80)
    plt.scatter([optimal_energy_batch], [optimal_energy], color="purple", s=80)

    plt.title("Latency, Energy, and Combined Cost vs Batch Size")
    plt.xlabel("Batch Size")
    plt.ylabel("Value")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    # ---- 3D Plot ----
    fig2 = plt.figure(figsize=(10, 7))
    ax = fig2.add_subplot(111, projection="3d")
    ax.plot(
        batch_sizes,
        latencies,
        zs=0,
        zdir="z",
        label="Latency",
        color="blue",
        marker="o",
    )
    ax.plot(
        batch_sizes, energies, zs=0, zdir="y", label="Energy", color="green", marker="^"
    )

    ax.set_xlabel("Batch Size")
    ax.set_ylabel("Latency (ms)")
    ax.set_zlabel("Energy (mJ)")
    ax.set_title("3D Plot: Latency and Energy vs Batch Size")
    ax.legend()
    plt.tight_layout()
    plt.show()

    fig2 = plt.figure(figsize=(10, 7))
    ax = fig2.add_subplot(111, projection="3d")
    ax.plot(
        batch_sizes,
        latencies,
        zs=0,
        zdir="z",
        label="Latency",
        color="blue",
        marker="o",
    )
    ax.plot(
        batch_sizes, energies, zs=0, zdir="y", label="Energy", color="green", marker="^"
    )

    ax.set_xlabel("Batch Size")
    ax.set_ylabel("Latency (ms)")
    ax.set_zlabel("Energy (mJ)")
    ax.set_title("3D Plot of Latency and Energy vs Batch Size")
    ax.legend()

    plt.show()
