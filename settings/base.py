import os

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Global variable to store command line arguments
_cmd_args = None


def set_cmd_args(args):
    """Set command line arguments for use in settings."""
    global _cmd_args
    _cmd_args = args


def get_setting(key, default, env_key=None, type_func=str):
    """
    Get setting value with priority: command line args → environment variables → defaults.

    Args:
        key: The setting key (used for command line args)
        default: Default value if not found elsewhere
        env_key: Environment variable key (if different from key)
        type_func: Function to convert the value (str, int, float, etc.)
    """
    if env_key is None:
        env_key = key.upper()

    # First priority: command line arguments
    if _cmd_args and hasattr(_cmd_args, key.replace("-", "_")):
        cmd_value = getattr(_cmd_args, key.replace("-", "_"))
        if cmd_value is not None:
            return type_func(cmd_value)

    # Second priority: environment variables
    env_value = os.getenv(env_key)
    if env_value is not None:
        return type_func(env_value)

    # Third priority: default value
    return type_func(default)


# Settings with priority system
MODE = get_setting("MODE", "Hybrid")
NUM_NODES = get_setting("MODE", 10, type_func=int)
MSGS_PER_NODE = get_setting("MSGS_PER_NODE", 15, type_func=int)
ENERGY_PER_BYTE = get_setting("ENERGY_PER_BYTE", 0.001, type_func=float)
MQTT_BROKER = get_setting("MQTT_BROKER", "localhost")
MQTT_PORT = get_setting("MQTT_PORT", 1883, type_func=int)
TOPIC = get_setting("TOPIC", "iot/biometric", "MQTT_TOPIC")
SHARED_SECRET_STR = get_setting("SHARED_SECRET", "my_shared_secret_key")
SHARED_SECRET = (
    SHARED_SECRET_STR.encode()
    if isinstance(SHARED_SECRET_STR, str)
    else SHARED_SECRET_STR
)
FHE_INTERVAL = get_setting("FHE_INTERVAL", 5, type_func=int)
BATTERY_THRESHOLD = get_setting("BATTERY_THRESHOLD", 20, type_func=int)
BATTERY_DEFAULT_VALUE = get_setting("BATTERY_DEFAULT_VALUE", 100, type_func=int)
POLY_MOD_DEGREE = get_setting("POLY_MOD_DEGREE", 4096, type_func=int)
REPLAY_WINDOW_SEC = get_setting(
    "REPLAY_WINDOW_SEC",
    60,
)
DRY_RUN = get_setting("DRY_RUN", False, type_func=bool)
try:
    from settings.local import *
except ImportError:
    pass

OUTPUT_FILE = "metrics_log"
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
LOGS_DIR = os.path.join(OUTPUT_DIR, "logs")
ANALYSIS_DIR = os.path.join(OUTPUT_DIR, "analysis")
F_P_DIR = os.path.join(BASE_DIR, "settings","fingerprints")

os.makedirs(LOGS_DIR, exist_ok=True)

LOG_CSV = os.path.join(
    LOGS_DIR,
    f"{OUTPUT_FILE}_{MODE}_{NUM_NODES}_{MSGS_PER_NODE}_{ENERGY_PER_BYTE}_{FHE_INTERVAL}_{BATTERY_THRESHOLD}.csv",
)
