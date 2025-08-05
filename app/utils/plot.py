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
    batch_sizes, latencies=None, energies=None, bytes=None, alpha=1.0
):
    # ---- Fit polynomials for each metric ----
    latency_coeffs = np.polyfit(batch_sizes, latencies, deg=2)
    energy_coeffs = np.polyfit(batch_sizes, energies, deg=2)
    bytes_coeffs = np.polyfit(batch_sizes, bytes, deg=2)

    # ---- Evaluate combined cost ----
    combined_costs = [
        combined_cost(lat, en, alpha) for lat, en in zip(latencies, energies)
    ]

    # ---- Optimal batch sizes ----
    optimal_latency_batch = round(-latency_coeffs[1] / (2 * latency_coeffs[0]))
    optimal_latency = np.polyval(latency_coeffs, optimal_latency_batch)

    optimal_energy_batch = round(-energy_coeffs[1] / (2 * energy_coeffs[0]))
    optimal_energy = np.polyval(energy_coeffs, optimal_energy_batch)

    optimal_bytes_batch = round(-bytes_coeffs[1] / (2 * bytes_coeffs[0]))
    optimal_bytes = np.polyval(bytes_coeffs, optimal_bytes_batch)

    if optimal_latency_batch < 0:
        optimal_latency_batch = 0

    # ---- Create figure with multiple Y axes ----
    fig, ax1 = plt.subplots(figsize=(12, 6))

    # Latency plot
    color1 = "tab:blue"
    ax1.set_xlabel("Batch Size")
    ax1.set_ylabel("Latency (ms)", color=color1)
    l1 = ax1.plot(batch_sizes, latencies, color=color1, marker='o', label="Latency")
    ax1.tick_params(axis='y', labelcolor=color1)
    ax1.axvline(optimal_latency_batch, color=color1, linestyle="--", alpha=0.6)
    ax1.scatter([optimal_latency_batch], [optimal_latency], color=color1, s=80)

    # Energy plot
    ax2 = ax1.twinx()
    color2 = "tab:green"
    ax2.set_ylabel("Energy (mJ)", color=color2)
    l2 = ax2.plot(batch_sizes, energies, color=color2, marker='s', label="Energy")
    ax2.tick_params(axis='y', labelcolor=color2)
    ax2.axvline(optimal_energy_batch, color=color2, linestyle="--", alpha=0.6)
    ax2.scatter([optimal_energy_batch], [optimal_energy], color=color2, s=80)

    # Bytes plot (3rd Y axis)
    ax3 = ax1.twinx()
    color3 = "tab:red"
    ax3.spines["right"].set_position(("outward", 60))
    ax3.set_ylabel("Bytes Sent", color=color3)
    l3 = ax3.plot(batch_sizes, bytes, color=color3, marker='^', label="Bytes")
    ax3.tick_params(axis='y', labelcolor=color3)
    ax3.axvline(optimal_bytes_batch, color=color3, linestyle="--", alpha=0.6)
    ax3.scatter([optimal_bytes_batch], [optimal_bytes], color=color3, s=80)

    # Combined cost on ax1 (optional overlay)
    l4 = ax1.plot(batch_sizes, combined_costs, color="gray", linestyle="--", marker="x", label="Combined Cost")

    # ---- Title and Legends ----
    plt.title("Latency, Energy, Bytes, and Combined Cost vs Batch Size")
    lines = l1 + l2 + l3 + l4
    labels = [line.get_label() for line in lines]
    ax1.legend(lines, labels, loc="upper left")
    plt.grid(True)
    plt.tight_layout()
    plt.show()

def dynamic_node_visualization(node_states, data_flows, steps=100, interval=200):
    """
    node_states: list of dicts [{"id": int, "pos": (x, y), "state": int}]
    data_flows: list of tuples (from_id, to_id, active: bool)
    steps: number of animation frames
    interval: ms between frames
    """
    fig, ax = plt.subplots()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect('equal')
    
    # Assign colors for states
    state_colors = ['gray', 'green', 'red', 'blue', 'orange']
    
    # Draw initial nodes
    scat = ax.scatter([n['pos'][0] for n in node_states],
                     [n['pos'][1] for n in node_states],
                     c=[state_colors[n['state'] % len(state_colors)] for n in node_states],
                     s=200, edgecolors='black')
    
    # Draw initial flows (arrows)
    arrows = []
    for flow in data_flows:
        from_node = next(n for n in node_states if n['id'] == flow[0])
        to_node = next(n for n in node_states if n['id'] == flow[1])
        arr = ax.annotate('', xy=to_node['pos'], xytext=from_node['pos'],
                          arrowprops=dict(arrowstyle='->', color='cyan' if flow[2] else 'gray', lw=2))
        arrows.append(arr)

    def update(frame):
        # Example: randomly change states and flows for demo
        for n in node_states:
            n['state'] = np.random.randint(0, len(state_colors))
        scat.set_color([state_colors[n['state'] % len(state_colors)] for n in node_states])
        # Randomly activate/deactivate flows
        for i, flow in enumerate(data_flows):
            active = np.random.rand() > 0.5
            data_flows[i] = (flow[0], flow[1], active)
            arrows[i].arrow_patch.set_color('cyan' if active else 'gray')
        return scat,

    ani = animation.FuncAnimation(fig, update, frames=steps, interval=interval, blit=False)
    plt.show()