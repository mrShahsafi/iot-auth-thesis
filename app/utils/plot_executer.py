from settings import DRY_RUN
from .plot import (
    plot_latency_energy_vs_batch_size,
    run_batch_analysis,
    setup_plot_latency_energy_vs_batch_size_data,
)


if __name__ == "__main__":
    # Run the analysis
    summary, opt_energy, opt_latency = run_batch_analysis(dry_run=DRY_RUN)

    print(f"\n=== FINAL RECOMMENDATIONS ===")
    print(f"For ENERGY efficiency, use batch size: {opt_energy}")
    print(f"For LATENCY efficiency, use batch size: {opt_latency}")

    # if opt_energy == opt_latency:
    #     print(f"Batch size {opt_energy} is optimal for both energy and latency!")
    # else:
    #     print(f"Trade-off exists between energy and latency optimization.")

    (
        batch_sizes,
        latencies,
        energies,
        bytes_,
    ) = setup_plot_latency_energy_vs_batch_size_data(
        batch_size_from=1,
        batch_size_to=15,
        nodes_number=10,
    )

    plot_latency_energy_vs_batch_size(
        batch_sizes=batch_sizes, latencies=latencies, energies=energies, bytes=bytes_
    )
