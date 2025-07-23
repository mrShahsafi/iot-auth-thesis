from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

NUM_NODES = 8
MSGS_PER_NODE = 15
ENERGY_PER_BYTE = 0.001
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
TOPIC = "iot/biometric"
SHARED_SECRET = b"my_shared_secret_key"
FHE_INTERVAL = 5
BATTERY_THRESHOLD = 20
BATTERY_DEFAULT_VALUE = 100
POLY_MOD_DEGREE = 4096

OUTPUT_FILE = "metrics_log_for_Hybrid_2_new_changesPy.csv"
REPLAY_WINDOW_SEC = 60
MODE = "Hybrid"
