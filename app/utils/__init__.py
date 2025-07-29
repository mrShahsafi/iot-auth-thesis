from .plot import (
    plot_energy_consumption,
    plot_boxplot_latency,
    plot_latency_energy_vs_batch_size,
)
from .metrics import create_output_csv
from .compress import compress_data
from .parser import parse_arguments
from .quadratic_regressoin import (
    estimate_latency,
    estimate_energy,
    estimate_combined_cost,
)
from .setup import setup_plot_latency_energy_vs_batch_size_data
