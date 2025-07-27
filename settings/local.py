# Import Local Settings
# MODE = get_setting("mode", "Hybrid")
# NUM_NODES = get_setting("num-nodes", 10, type_func=int)
# MSGS_PER_NODE = get_setting("msgs-per-node", 15, type_func=int)
# ENERGY_PER_BYTE = get_setting("energy-per-byte", 0.001, type_func=float)
# MQTT_BROKER = get_setting("mqtt-broker", "localhost")
# MQTT_PORT = get_setting("mqtt-port", 1883, type_func=int)
# TOPIC = get_setting("topic", "iot/biometric", "MQTT_TOPIC")
# SHARED_SECRET_STR = get_setting("shared-secret", "my_shared_secret_key")
# SHARED_SECRET = (
#     SHARED_SECRET_STR.encode()
#     if isinstance(SHARED_SECRET_STR, str)
#     else SHARED_SECRET_STR
# )
# FHE_INTERVAL = get_setting("fhe-interval", 5, type_func=int)
# BATTERY_THRESHOLD = get_setting("battery-threshold", 20, type_func=int)
# BATTERY_DEFAULT_VALUE = get_setting("battery-default", 100, type_func=int)
# POLY_MOD_DEGREE = get_setting("poly-mod-degree", 4096, type_func=int)

# OUTPUT_FILE = "metrics_log"
# OUTPUT_DIR = f"{BASE_DIR}/output/"
# LOG_CSV = f"{OUTPUT_DIR}/logs/{OUTPUT_FILE}_{MODE}_{NUM_NODES}_{MSGS_PER_NODE}_{ENERGY_PER_BYTE}_{FHE_INTERVAL}_{BATTERY_THRESHOLD}.csv"
# REPLAY_WINDOW_SEC = 60