import matplotlib.pyplot as plt
import pandas as pd

from settings import OUTPUT_FILE, MODE, OUTPUT_DIR, LOG_CSV


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
