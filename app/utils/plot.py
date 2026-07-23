import pandas as pd
import numpy as np
import os
import glob
import matplotlib
import matplotlib.pyplot as plt

from settings import OUTPUT_FILE, MODE, OUTPUT_DIR, LOG_CSV, NUM_NODES, DRY_RUN

from .quadratic_regressoin import combined_cost

is_interactive = matplotlib.get_backend() in matplotlib.rcsetup.interactive_bk


def plot_energy_consumption(nodes, energy_values, dry_run=DRY_RUN):
    plt.figure(figsize=(8, 4))
    plt.bar(nodes, energy_values, color="purple")
    plt.xlabel("Node ID")
    plt.ylabel("Energy Consumed (mJ)")
    plt.title(
        f"Energy Consumption per Node - Adaptive Batching & Crypto (Nodes: {NUM_NODES})"
    )
    plt.grid(axis="y")
    plt.tight_layout()

    if not dry_run:
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
    l1 = ax1.plot(batch_sizes, latencies, color=color1, marker="o", label="Latency")
    ax1.tick_params(axis="y", labelcolor=color1)
    ax1.axvline(optimal_latency_batch, color=color1, linestyle="--", alpha=0.6)
    ax1.scatter([optimal_latency_batch], [optimal_latency], color=color1, s=80)

    # Energy plot
    ax2 = ax1.twinx()
    color2 = "tab:green"
    ax2.set_ylabel("Energy (mJ)", color=color2)
    l2 = ax2.plot(batch_sizes, energies, color=color2, marker="s", label="Energy")
    ax2.tick_params(axis="y", labelcolor=color2)
    ax2.axvline(optimal_energy_batch, color=color2, linestyle="--", alpha=0.6)
    ax2.scatter([optimal_energy_batch], [optimal_energy], color=color2, s=80)

    # Bytes plot (3rd Y axis)
    ax3 = ax1.twinx()
    color3 = "tab:red"
    ax3.spines["right"].set_position(("outward", 60))
    ax3.set_ylabel("Bytes Sent", color=color3)
    l3 = ax3.plot(batch_sizes, bytes, color=color3, marker="^", label="Bytes")
    ax3.tick_params(axis="y", labelcolor=color3)
    ax3.axvline(optimal_bytes_batch, color=color3, linestyle="--", alpha=0.6)
    ax3.scatter([optimal_bytes_batch], [optimal_bytes], color=color3, s=80)

    # Combined cost on ax1 (optional overlay)
    l4 = ax1.plot(
        batch_sizes,
        combined_costs,
        color="gray",
        linestyle="--",
        marker="x",
        label="Combined Cost",
    )

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
    ax.set_aspect("equal")

    # Assign colors for states
    state_colors = ["gray", "green", "red", "blue", "orange"]

    # Draw initial nodes
    scat = ax.scatter(
        [n["pos"][0] for n in node_states],
        [n["pos"][1] for n in node_states],
        c=[state_colors[n["state"] % len(state_colors)] for n in node_states],
        s=200,
        edgecolors="black",
    )

    # Draw initial flows (arrows)
    arrows = []
    for flow in data_flows:
        from_node = next(n for n in node_states if n["id"] == flow[0])
        to_node = next(n for n in node_states if n["id"] == flow[1])
        arr = ax.annotate(
            "",
            xy=to_node["pos"],
            xytext=from_node["pos"],
            arrowprops=dict(arrowstyle="->", color="cyan" if flow[2] else "gray", lw=2),
        )
        arrows.append(arr)

    def update(frame):
        # Example: randomly change states and flows for demo
        for n in node_states:
            n["state"] = np.random.randint(0, len(state_colors))
        scat.set_color(
            [state_colors[n["state"] % len(state_colors)] for n in node_states]
        )
        # Randomly activate/deactivate flows
        for i, flow in enumerate(data_flows):
            active = np.random.rand() > 0.5
            data_flows[i] = (flow[0], flow[1], active)
            arrows[i].arrow_patch.set_color("cyan" if active else "gray")
        return (scat,)

    # ani = animation.FuncAnimation(
    #     fig, update, frames=steps, interval=interval, blit=False
    # )
    plt.show()


def plot_batch_efficiency_summary(
    path=None,
):
    _csv_dir = path or f"{OUTPUT_DIR}/batch_efficiency_summary.csv"
    # Load your CSV file
    df = pd.read_csv(_csv_dir)
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, axes = plt.subplots(3, 1, figsize=(10, 12))

    # --- Latency plot ---
    axes[0].errorbar(
        df["batch_size"],
        df["avg_latency"],
        yerr=df["std_latency"],
        fmt="-o",
        capsize=4,
        label="Avg Latency",
    )
    axes[0].fill_between(
        df["batch_size"],
        df["min_latency"],
        df["max_latency"],
        alpha=0.2,
        label="Latency Range",
    )
    axes[0].set_title("Latency vs Batch Size")
    axes[0].set_xlabel("Batch Size")
    axes[0].set_ylabel("Latency (ms)")
    axes[0].legend()

    # --- Energy plot ---
    axes[1].errorbar(
        df["batch_size"],
        df["total_energy"],
        yerr=df["std_energy"],
        fmt="-s",
        capsize=4,
        color="green",
        label="Avg Energy",
    )
    axes[1].fill_between(
        df["batch_size"],
        df["min_energy"],
        df["max_energy"],
        alpha=0.2,
        color="green",
        label="Energy Range",
    )
    axes[1].set_title("Energy Consumption vs Batch Size")
    axes[1].set_xlabel("Batch Size")
    axes[1].set_ylabel("Energy (J)")
    axes[1].legend()

    # --- Battery and Node Count plot ---
    ax2 = axes[2].twinx()
    axes[2].plot(
        df["batch_size"], df["avg_battery"], "-^", label="Avg Battery (%)", color="blue"
    )
    ax2.plot(
        df["batch_size"], df["node_count"], "--o", label="Node Count", color="orange"
    )
    axes[2].set_title("Battery and Node Count vs Batch Size")
    axes[2].set_xlabel("Batch Size")
    axes[2].set_ylabel("Battery (%)")
    ax2.set_ylabel("Node Count")

    axes[2].legend(loc="upper left")
    ax2.legend(loc="upper right")

    plt.tight_layout()
    plt.show()


def load_batch_data_from_csvs(csv_directory=None, dry_run=False):
    """
    Load data from multiple CSV files generated by batch runs.

    Args:
        csv_directory: Directory containing CSV files. If None, uses OUTPUT_DIR/logs
        dry_run (bool, optional): If True, runs analysis without executing plotting or file writes.


    Returns:
        dict: Dictionary with batch_size as key and DataFrame as value
    """
    if csv_directory is None:
        csv_directory = os.path.join(OUTPUT_DIR, "logs")

    # Find all CSV files from batch runs
    csv_pattern = os.path.join(csv_directory, "metrics_log_Hybrid_10_*_*_*_20.csv")
    csv_files = glob.glob(csv_pattern)

    batch_data = {}

    for csv_file in csv_files:
        try:
            # Extract FHE_INTERVAL from filename
            filename = os.path.basename(csv_file)
            parts = filename.replace(".csv", "").split("_")

            if len(parts) >= 7:
                fhe_interval = int(parts[-2])  # FHE_INTERVAL is second to last

                # Read CSV data
                df = pd.read_csv(csv_file)
                df["batch_size"] = fhe_interval  # Add batch size column
                batch_data[fhe_interval] = df

                print(f"Loaded batch {fhe_interval}: {len(df)} nodes")

        except Exception as e:
            print(f"Error processing {csv_file}: {e}")

    return batch_data


def analyze_batch_efficiency(batch_data, dry_run=False):
    """
    Analyze energy and latency efficiency across batch sizes.

    Args:
        batch_data: Dictionary from load_batch_data_from_csvs()
        dry_run (bool, optional): If True, runs analysis without executing plotting or file writes.


    Returns:
        tuple: (summary_df, optimal_energy_batch, optimal_latency_batch)
    """
    summary_data = []

    for batch_size in sorted(batch_data.keys()):
        df = batch_data[batch_size]
        energy_sum_by_node = df.groupby("node_id")["energy"].sum()
        latency_sum_by_node = df.groupby("node_id")["latency_ms"].sum()
        battrey_sum_by_node = df.groupby("node_id")["battery"].sum()
        # Calculate statistics for this batch
        stats = {
            "batch_size": batch_size,
            # "avg_latency": df["latency_ms"].mean(),
            "avg_latency": latency_sum_by_node.mean(),
            "std_latency": df["latency_ms"].std(),
            "min_latency": df["latency_ms"].min(),
            "max_latency": df["latency_ms"].max(),
            # "avg_energy": df["energy"].mean(),
            "avg_energy": energy_sum_by_node.mean(),
            "std_energy": df["energy"].std(),
            "min_energy": df["energy"].min(),
            "max_energy": df["energy"].max(),
            "total_energy": df["energy"].sum(),
            # "avg_battery": df["battery"].mean(),
            "avg_battery": battrey_sum_by_node.mean(),
            "min_battery": df["battery"].min(),
            "node_count": len(df),
        }
        summary_data.append(stats)

    summary_df = pd.DataFrame(summary_data)

    # Find optimal batch sizes
    optimal_energy_batch = summary_df.loc[
        summary_df["avg_energy"].idxmin(), "batch_size"
    ]
    optimal_latency_batch = summary_df.loc[
        summary_df["avg_latency"].idxmin(), "batch_size"
    ]

    return summary_df, optimal_energy_batch, optimal_latency_batch


def plot_comprehensive_batch_analysis(
    batch_data=None, csv_directory=None, save_plots=True, dry_run=False
):
    """
    Create comprehensive plots showing energy and latency analysis across batch sizes.

    Args:
        batch_data: Pre-loaded batch data. If None, loads from csv_directory
        csv_directory: Directory containing CSV files
        save_plots: Whether to save plots to files
        dry_run (bool, optional): If True, runs analysis without executing plotting or file writes.

    """
    # Load data if not provided
    if batch_data is None:
        batch_data = load_batch_data_from_csvs(csv_directory)

    if not batch_data:
        print("No batch data found!")
        return

    if dry_run:
        save_plots = False
    # Analyze efficiency
    summary_df, optimal_energy_batch, optimal_latency_batch = analyze_batch_efficiency(
        batch_data
    )

    print(f"\n=== BATCH EFFICIENCY ANALYSIS ===")
    print(f"Optimal batch size for ENERGY efficiency: {optimal_energy_batch}")
    print(f"Optimal batch size for LATENCY efficiency: {optimal_latency_batch}")
    print(
        f"Energy at optimal batch: {summary_df[summary_df['batch_size']==optimal_energy_batch]['avg_energy'].iloc[0]:.3f} mJ"
    )
    print(
        f"Latency at optimal batch: {summary_df[summary_df['batch_size']==optimal_latency_batch]['avg_latency'].iloc[0]:.2f} ms"
    )

    # Create plots directory
    if save_plots:
        plots_dir = os.path.join(OUTPUT_DIR, "plots")
        os.makedirs(plots_dir, exist_ok=True)

    # Check if we're in an interactive backend
    is_interactive = matplotlib.get_backend() in matplotlib.rcsetup.interactive_bk

    # ============ PLOT 1: Individual Node Performance by Batch Size ============
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12))

    # Energy consumption per node
    batch_sizes = sorted(batch_data.keys())
    colors = plt.cm.viridis(np.linspace(0, 1, len(batch_sizes)))

    for i, batch_size in enumerate(batch_sizes):
        df = batch_data[batch_size]
        ax1.scatter(
            [batch_size] * len(df),
            df["energy"],
            alpha=0.6,
            color=colors[i],
            s=50,
            label=f"Batch {batch_size}",
        )

    # Add average line
    ax1.plot(
        batch_sizes,
        summary_df["avg_energy"],
        linewidth=2,
        markersize=8,
        label="Average Energy",
        color="red",
        marker="o",
    )

    # Mark optimal point
    # ax1.axvline(
    #     x=optimal_energy_batch,
    #     color="green",
    #     linestyle="--",
    #     linewidth=2,
    #     label=f"Optimal Energy (Batch {optimal_energy_batch})",
    # )

    ax1.set_xlabel("Batch Size (FHE Interval)")
    ax1.set_ylabel("Energy Consumption (mJ)")
    ax1.set_title("Energy Consumption per Node Across Batch Sizes")
    ax1.grid(True, alpha=0.3)
    ax1.legend(bbox_to_anchor=(1.05, 1), loc="upper left")

    # Latency per node
    for i, batch_size in enumerate(batch_sizes):
        df = batch_data[batch_size]
        ax2.scatter(
            [batch_size] * len(df), df["latency_ms"], alpha=0.6, color=colors[i], s=50
        )

    # Add average line
    ax2.plot(
        batch_sizes,
        summary_df["avg_latency"],
        linewidth=2,
        markersize=8,
        label="Average Latency",
        color="blue",
        marker="o",
    )

    # Mark optimal point
    # ax2.axvline(
    #     x=optimal_latency_batch,
    #     color="orange",
    #     linestyle="--",
    #     linewidth=2,
    #     label=f"Optimal Latency (Batch {optimal_latency_batch})",
    # )

    ax2.set_xlabel("Batch Size (FHE Interval)")
    ax2.set_ylabel("Latency (ms)")
    ax2.set_title("Latency per Node Across Batch Sizes")
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    plt.tight_layout()
    if save_plots:
        plt.savefig(
            os.path.join(
                plots_dir, f"individual_node_performance_{NUM_NODES}nodes.png"
            ),
            dpi=300,
            bbox_inches="tight",
        )
        plt.close(fig)
    elif is_interactive:
        plt.show()

    # ============ PLOT 2: Summary Statistics with Error Bars ============
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    # Energy efficiency plot
    ax1.errorbar(
        summary_df["batch_size"],
        summary_df["avg_energy"],
        yerr=summary_df["std_energy"],
        fmt="o-",
        capsize=5,
        capthick=2,
        color="purple",
        linewidth=2,
        markersize=8,
    )
    ax1.fill_between(
        summary_df["batch_size"],
        summary_df["avg_energy"] - summary_df["std_energy"],
        summary_df["avg_energy"] + summary_df["std_energy"],
        alpha=0.2,
        color="purple",
    )

    # Mark optimal point
    # optimal_energy_row = summary_df[
    #     summary_df["batch_size"] == optimal_energy_batch
    # ].iloc[0]
    # ax1.scatter(
    #     [optimal_energy_batch],
    #     [optimal_energy_row["avg_energy"]],
    #     color="green",
    #     s=150,
    #     marker="*",
    #     zorder=5,
    #     label=f"Optimal: Batch {optimal_energy_batch}",
    # )

    ax1.set_xlabel("Batch Size (FHE Interval)")
    ax1.set_ylabel("Average Energy Consumption (mJ)")
    ax1.set_title("Energy Efficiency Analysis")
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    # Latency efficiency plot
    ax2.errorbar(
        summary_df["batch_size"],
        summary_df["avg_latency"],
        yerr=summary_df["std_latency"],
        fmt="o-",
        capsize=5,
        capthick=2,
        color="blue",
        linewidth=2,
        markersize=8,
    )
    ax2.fill_between(
        summary_df["batch_size"],
        summary_df["avg_latency"] - summary_df["std_latency"],
        summary_df["avg_latency"] + summary_df["std_latency"],
        alpha=0.2,
        color="blue",
    )

    # Mark optimal point
    # optimal_latency_row = summary_df[
    #     summary_df["batch_size"] == optimal_latency_batch
    # ].iloc[0]
    # ax2.scatter(
    #     [optimal_latency_batch],
    #     [optimal_latency_row["avg_latency"]],
    #     color="orange",
    #     s=150,
    #     marker="*",
    #     zorder=5,
    #     label=f"Optimal: Batch {optimal_latency_batch}",
    # )

    ax2.set_xlabel("Batch Size (FHE Interval)")
    ax2.set_ylabel("Average Latency (ms)")
    ax2.set_title("Latency Efficiency Analysis")
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    plt.tight_layout()
    if save_plots:
        plt.savefig(
            os.path.join(plots_dir, f"efficiency_analysis_{NUM_NODES}nodes.png"),
            dpi=300,
            bbox_inches="tight",
        )
        plt.close(fig)
    elif is_interactive:
        plt.show()

    # ============ PLOT 3: Combined Efficiency Trade-off ============
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))

    # Normalize metrics for comparison (0-1 scale)
    norm_energy = (summary_df["avg_energy"] - summary_df["avg_energy"].min()) / (
        summary_df["avg_energy"].max() - summary_df["avg_energy"].min()
    )
    norm_latency = (summary_df["avg_latency"] - summary_df["avg_latency"].min()) / (
        summary_df["avg_latency"].max() - summary_df["avg_latency"].min()
    )

    # Plot normalized metrics
    ax.plot(
        summary_df["batch_size"],
        norm_energy,
        "o-",
        linewidth=3,
        markersize=8,
        color="purple",
        label="Normalized Energy",
    )
    ax.plot(
        summary_df["batch_size"],
        norm_latency,
        "s-",
        linewidth=3,
        markersize=8,
        color="blue",
        label="Normalized Latency",
    )

    # Combined score (equal weights)
    combined_score = (norm_energy + norm_latency) / 2
    ax.plot(
        summary_df["batch_size"],
        combined_score,
        "^-",
        linewidth=3,
        markersize=8,
        color="red",
        label="Combined Score",
    )

    # Find optimal combined point
    # optimal_combined_batch = summary_df.loc[combined_score.idxmin(), "batch_size"]
    # ax.axvline(
    #     x=optimal_combined_batch,
    #     color="red",
    #     linestyle="--",
    #     linewidth=2,
    #     label=f"Optimal Combined (Batch {optimal_combined_batch})",
    # )

    # Mark individual optimal points
    # ax.axvline(
    #     x=optimal_energy_batch,
    #     color="purple",
    #     linestyle=":",
    #     alpha=0.7,
    #     label=f"Energy Optimal (Batch {optimal_energy_batch})",
    # )
    # ax.axvline(
    #     x=optimal_latency_batch,
    #     color="blue",
    #     linestyle=":",
    #     alpha=0.7,
    #     label=f"Latency Optimal (Batch {optimal_latency_batch})",
    # )

    ax.set_xlabel("Batch Size (FHE Interval)")
    ax.set_ylabel("Normalized Score (0=Best, 1=Worst)")
    ax.set_title("Combined Efficiency Trade-off Analysis")
    ax.grid(True, alpha=0.3)
    ax.legend()
    ax.set_ylim(-0.05, 1.05)

    plt.tight_layout()
    if save_plots:
        plt.savefig(
            os.path.join(plots_dir, f"combined_tradeoff_{NUM_NODES}nodes.png"),
            dpi=300,
            bbox_inches="tight",
        )
        plt.close(fig)
    elif is_interactive:
        plt.show()

    # ============ PLOT 4: Battery Impact Analysis ============
    fig, ax = plt.subplots(1, 1, figsize=(12, 6))

    # Box plot of battery levels by batch size
    battery_by_batch = [batch_data[batch]["battery"].values for batch in batch_sizes]

    # Use tick_labels instead of labels to avoid deprecation warning
    box_plot = ax.boxplot(battery_by_batch, tick_labels=batch_sizes, patch_artist=True)

    # Color the boxes
    colors = plt.cm.RdYlGn(np.linspace(0.2, 0.8, len(batch_sizes)))
    for patch, color in zip(box_plot["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)

    ax.set_xlabel("Batch Size (FHE Interval)")
    ax.set_ylabel("Battery Level (%)")
    ax.set_title("Battery Levels Distribution by Batch Size")
    ax.grid(True, alpha=0.3)

    # Add horizontal line at battery threshold (if available)
    ax.axhline(y=20, color="red", linestyle="--", alpha=0.7, label="Battery Threshold")
    ax.legend()

    plt.tight_layout()
    if save_plots:
        plt.savefig(
            os.path.join(plots_dir, f"battery_analysis_{NUM_NODES}nodes.png"),
            dpi=300,
            bbox_inches="tight",
        )
        plt.close(fig)
    elif is_interactive:
        plt.show()

    # ============ SAVE SUMMARY DATA ============
    if save_plots:
        summary_file = os.path.join(OUTPUT_DIR, "batch_efficiency_summary.csv")
        summary_df.to_csv(summary_file, index=False)
        print(f"\nSummary data saved to: {summary_file}")

    # Print detailed summary
    print(f"\n=== DETAILED EFFICIENCY SUMMARY ===")
    print(summary_df.round(3))

    return summary_df, optimal_energy_batch, optimal_latency_batch


# Convenience function to run the analysis
def run_batch_analysis(csv_directory: str = None, dry_run: bool = False):
    """
    Main function to run the complete batch analysis.

    Args:
        csv_directory: Directory containing CSV files. If None, uses OUTPUT_DIR/logs
        dry_run (bool, optional): If True, runs analysis without executing plotting or file writes.


    Returns:
        tuple: (summary_df, optimal_energy_batch, optimal_latency_batch)
    """
    print("Starting comprehensive batch analysis...")
    return plot_comprehensive_batch_analysis(
        csv_directory=csv_directory, dry_run=dry_run
    )


def setup_plot_latency_energy_vs_batch_size_data(
    batch_size_from: int,
    batch_size_to: int,
    nodes_number: int = 10,
) -> tuple[list[int], list[float], list[float], list[float]]:

    _directory = f"{OUTPUT_DIR}/logs"
    _batch_sizes = []
    _latencies = []
    _energies = []
    _bytes = []

    for b in range(batch_size_from, batch_size_to + 1):
        file_name = f"/metrics_log_Hybrid_{nodes_number}_15_0.001_{b}_5.csv"
        file_path = _directory + file_name
        df = pd.read_csv(file_path)
        _batch_sizes.append(b)
        # energy calc
        energy_sum_by_node = df.groupby("node_id")["energy"].sum()
        mean_of_node_sums_energy = energy_sum_by_node.mean()
        # latency calc
        latency_sum_by_node = df.groupby("node_id")["latency_ms"].sum()
        mean_of_node_sums_latency = latency_sum_by_node.mean()
        # bytes calc
        bytes_sum_by_node = df.groupby("node_id")["bytes"].sum()
        mean_of_node_sums_bytes = bytes_sum_by_node.mean()
        #
        _energies.append(float(mean_of_node_sums_energy))
        _latencies.append(float(mean_of_node_sums_latency))
        _bytes.append(float(mean_of_node_sums_bytes))

    return _batch_sizes, _latencies, _energies, _bytes


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
