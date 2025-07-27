from settings import (
    MODE,
    OUTPUT_FILE,
    NUM_NODES,
    LOG_CSV,
    MSGS_PER_NODE,
    ENERGY_PER_BYTE,
    MQTT_BROKER,
    MQTT_PORT,
    TOPIC,
    SHARED_SECRET,
    FHE_INTERVAL,
    BATTERY_THRESHOLD,
    BATTERY_DEFAULT_VALUE,
    POLY_MOD_DEGREE,
)
import argparse


def parse_arguments():
    """Parse command line arguments with defaults from settings."""
    parser = argparse.ArgumentParser(
        description="IoT Biometric Authentication Simulation"
    )

    parser.add_argument(
        "--mode", type=str, default=MODE, help=f"Operation mode (default: {MODE})"
    )
    parser.add_argument(
        "--num-nodes",
        type=int,
        default=NUM_NODES,
        help=f"Number of IoT nodes (default: {NUM_NODES})",
    )
    parser.add_argument(
        "--msgs-per-node",
        type=int,
        default=MSGS_PER_NODE,
        help=f"Messages per node (default: {MSGS_PER_NODE})",
    )
    parser.add_argument(
        "--energy-per-byte",
        type=float,
        default=ENERGY_PER_BYTE,
        help=f"Energy consumption per byte (default: {ENERGY_PER_BYTE})",
    )
    parser.add_argument(
        "--mqtt-broker",
        type=str,
        default=MQTT_BROKER,
        help=f"MQTT broker address (default: {MQTT_BROKER})",
    )
    parser.add_argument(
        "--mqtt-port",
        type=int,
        default=MQTT_PORT,
        help=f"MQTT broker port (default: {MQTT_PORT})",
    )
    parser.add_argument(
        "--topic", type=str, default=TOPIC, help=f"MQTT topic (default: {TOPIC})"
    )
    parser.add_argument(
        "--shared-secret",
        type=str,
        default=SHARED_SECRET.decode()
        if isinstance(SHARED_SECRET, bytes)
        else SHARED_SECRET,
        help="Shared secret key",
    )
    parser.add_argument(
        "--fhe-interval",
        type=int,
        default=FHE_INTERVAL,
        help=f"FHE interval (default: {FHE_INTERVAL})",
    )
    parser.add_argument(
        "--battery-threshold",
        type=int,
        default=BATTERY_THRESHOLD,
        help=f"Battery threshold (default: {BATTERY_THRESHOLD})",
    )
    parser.add_argument(
        "--battery-default",
        type=int,
        default=BATTERY_DEFAULT_VALUE,
        help=f"Default battery value (default: {BATTERY_DEFAULT_VALUE})",
    )
    parser.add_argument(
        "--poly-mod-degree",
        type=int,
        default=POLY_MOD_DEGREE,
        help=f"Polynomial modulus degree (default: {POLY_MOD_DEGREE})",
    )

    return parser.parse_args()
