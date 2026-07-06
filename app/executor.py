import threading
from settings import MODE, NUM_NODES
from .nodes import gateway, plain_iot_node, hybrid_iot_node
from .utils import plot_energy_consumption, plot_boxplot_latency
from .initializer import init_app


def main(dry_run=False):
    """Main execution function."""
    # Initialize application components
    context, energy_consumption, recent_timestamps, lock, trusted_database = init_app(
        dry_run=dry_run
    )
    threads = []
    # Start gateway thread
    gw_thread = threading.Thread(
        target=gateway, args=(context, trusted_database, recent_timestamps, dry_run)
    )
    gw_thread.start()
    threads.append(gw_thread)

    # Start IoT node threads
    iot_node_mode = {"Hybrid": hybrid_iot_node, "Plain": plain_iot_node}

    for node_id in range(NUM_NODES):
        t = threading.Thread(
            target=iot_node_mode.get(MODE, None),
            args=(
                node_id,
                context,
                lock,
                energy_consumption,
                None,
                None,
                trusted_database,
            ),
        )
        t.start()
        threads.append(t)

    # Wait for all threads to complete
    for t in threads:
        t.join()

    # Generate and display results
    nodes = list(energy_consumption.keys())
    energy_values = list(energy_consumption.values())
    print("\nTotal Energy Consumption (mJ):")
    for node, energy in energy_consumption.items():
        print(f"Node {node}: {energy:.2f} mJ")
    if not dry_run:
        print("Running the plots...")
        plot_energy_consumption(nodes, energy_values)
        plot_boxplot_latency()
