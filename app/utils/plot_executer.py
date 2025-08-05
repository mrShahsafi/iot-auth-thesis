import pandas as pd
from settings import OUTPUT_DIR

from .plot import plot_latency_energy_vs_batch_size

BATCH_SIZE_FROM = 1
BATCH_SIZE_TO = 15
NODES_NUMBER = 10


def setup_plot_latency_energy_vs_batch_size_data(
    batch_size_from: int,
    batch_size_to: int,
    nodes_number: int = 10,
) -> tuple[list[int], list[float], list[float],list[float]]:
    _directory = f"{OUTPUT_DIR}logs"
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

    return _batch_sizes, _latencies, _energies,_bytes



(
    batch_sizes , latencies , energies,bytes
) = setup_plot_latency_energy_vs_batch_size_data(
    batch_size_from=BATCH_SIZE_FROM,
    batch_size_to=BATCH_SIZE_TO,
    nodes_number=NODES_NUMBER,
)

plot_latency_energy_vs_batch_size(
    batch_sizes=batch_sizes,
    latencies=latencies,
    energies=energies,
    bytes=bytes
)
