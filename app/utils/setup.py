import pandas as pd

from settings import OUTPUT_DIR
from app.utils.plot import plot_latency_energy_vs_batch_size


def setup_plot_latency_energy_vs_batch_size_data(batch_size: int):
    directory = f"{OUTPUT_DIR}/logs/"
    batch_sizes = []
    latencies = []
    energies = []

    for b in range(1, batch_size + 1):
        file_name = f"metrics_log_Hybrid_10_15_0.001_{b}_20.csv"
        file_path = directory + file_name
        df = pd.read_csv(file_path)
        batch_sizes.append(b)
        energy_sum_by_node = df.groupby("node_id")["energy"].sum()
        mean_of_node_sums_energy = energy_sum_by_node.mean()
        latency_sum_by_node = df.groupby("node_id")["latency_ms"].sum()
        mean_of_node_sums_latency = latency_sum_by_node.mean()
        latencies.append(float(mean_of_node_sums_latency))
        energies.append(float(mean_of_node_sums_energy))

    return batch_sizes, latencies, energies


if __name__ == "__main__":

    plot_latency_energy_vs_batch_size(
        batch_sizes=batch_sizes,
        latencies=latencies,
        energies=energies,
    )
