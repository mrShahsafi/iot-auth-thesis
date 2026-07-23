# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/__init__.py =====




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/merged.py =====




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/settings/local.py =====
# Import Local Settings
MODE = "Hybrid"
NUM_NODES = 10
MSGS_PER_NODE = 15
# FHE_INTERVAL = 10
BATTERY_THRESHOLD = 5
POLY_MOD_DEGREE = 4096

"""
1024
بسیار ضعیف
فقط آموزش و تست سریع
2048
ضعیف
برای toy example‌ها
4096
متوسط (≈ 96-bit)
low precision FHE
8192
قابل قبول (≈ 128-bit)
balance بین امنیت و performance
16384
قوی (≈ 192-bit)
برای precision بالا یا داده‌های حساس
32768



"""




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/settings/__init__.py =====
from .base import *

print(
    f"You are in the {MODE} mode, with {NUM_NODES} nodes and {FHE_INTERVAL} batch sizing."
)
print(f"DIR: {BASE_DIR}")




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/settings/base.py =====
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




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/app/run.py =====
from .executor import main

from settings import DRY_RUN

if __name__ == "__main__":
    main(dry_run=DRY_RUN)




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/app/__init__.py =====




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/app/initializer.py =====
import sys
import os
import threading
from collections import defaultdict, deque

from settings import MODE, OUTPUT_FILE, NUM_NODES, LOG_CSV
from .utils import create_output_csv
from .core import tensor_context, init_energy_consumption, generate_biometric_vector


def init_app(dry_run=False):
    """Initialize application components and global variables."""
    # Add root of project to path
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    context = tensor_context()
    energy_consumption = init_energy_consumption()
    recent_timestamps = defaultdict(lambda: deque(maxlen=100))

    if not dry_run:
        create_output_csv()

    lock = threading.Lock()
    trusted_database = generate_biometric_vector()

    return context, energy_consumption, recent_timestamps, lock, trusted_database




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/app/executor.py =====
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




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/app/core/auth.py =====




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/app/core/encryption.py =====
import hmac
import hashlib

from settings import SHARED_SECRET


def generate_hmac(message: str) -> str:
    return hmac.new(SHARED_SECRET, message.encode(), hashlib.sha256).hexdigest()




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/app/core/biometrics.py =====
import os
import random

from skimage.feature import hog
from skimage import io, color
import numpy as np

from settings import NUM_NODES, F_P_DIR


def load_fingerprint_vectors(dataset_dir=None):
    dataset_dir = dataset_dir or F_P_DIR
    print(f"loading fingerprint Dataset from : {dataset_dir}.")
    vectors = {}
    for i, fname in enumerate(sorted(os.listdir(dataset_dir))):
        img = io.imread(os.path.join(dataset_dir, fname))
        if img.ndim == 3:
            img = color.rgb2gray(img)
        features, _ = hog(
            img,
            orientations=9,
            pixels_per_cell=(8, 8),
            cells_per_block=(1, 1),
            visualize=True,
            feature_vector=True,
        )
        vectors[i] = features[:12]  # or :81 based on your setup
    return vectors


def generate_biometric_vector(
    biometric_type="fingerprint", nodes_number=None, env="real"
):
    _nodes_number = nodes_number or NUM_NODES
    if biometric_type == "fingerprint":
        if not env == "real":
            trusted_database = {i: random.randint(1000, 9999) for i in range(NUM_NODES)}
        else:
            _vectors = load_fingerprint_vectors()
            trusted_database = _vectors
    else:
        trusted_database = {i: i * 1000 + 1234 for i in range(NUM_NODES)}

    return trusted_database




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/app/core/__init__.py =====
from .encryption import generate_hmac
from .tenseal import tensor_context
from .energy import init_energy_consumption
from .biometrics import generate_biometric_vector, load_fingerprint_vectors




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/app/core/energy.py =====
from settings import NUM_NODES


def init_energy_consumption(init_value=0.0, num_nodes=None):
    _num_nodes = num_nodes or NUM_NODES
    energy_consumption = {node: init_value for node in range(_num_nodes)}
    return energy_consumption




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/app/core/tenseal.py =====
import tenseal as ts

from settings import POLY_MOD_DEGREE


def tensor_context():
    context = ts.context(
        ts.SCHEME_TYPE.BFV, poly_modulus_degree=POLY_MOD_DEGREE, plain_modulus=1032193
    )
    context.generate_galois_keys()
    context.generate_relin_keys()
    context.global_scale = 2**40
    return context




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/app/nodes/gateway.py =====
import time
import hmac
import tenseal as ts
import paho.mqtt.client as mqtt
import json
import base64
import gzip

from collections import deque


from settings import (
    TOPIC,
    REPLAY_WINDOW_SEC,
    MQTT_PORT,
    MQTT_BROKER,
    MSGS_PER_NODE,
    NUM_NODES,
    LOG_CSV,
    MODE,
)
from ..core import generate_hmac


def gateway(context, trusted_database, recent_timestamps, dry_run=False):
    client = mqtt.Client()
    received_count = 0
    expected_count = NUM_NODES * MSGS_PER_NODE

    def on_connect(client, userdata, flags, rc):
        client.subscribe(TOPIC)

    def on_message(client, userdata, msg):
        nonlocal received_count

        if MODE == "Hybrid":
            compressed_payload = base64.b64decode(msg.payload)
            decompressed_json = gzip.decompress(compressed_payload).decode("utf-8")
            payload = json.loads(decompressed_json)
        else:
            payload = json.loads(msg.payload.decode("utf-8"))
        receive_time_ns = time.time_ns()
        node_id = payload["node_id"]
        timestamp = (
            payload.get("timestamp") or payload.get("batch_timestamps", [None])[0]
        )
        if "enc_biometrics" in payload:
            base_latency = receive_time_ns - payload["batch_timestamps"][0] * 1e9
            latency_ms = base_latency / 1_000_000

        else:
            latency_ms = (receive_time_ns - payload["send_time_ns"]) / 1_000_000

        if not is_fresh(node_id, timestamp):
            print(f"[Gateway] Replay detected from Node {node_id}")
            return
        received_count += 1
        if not dry_run:
            try:
                with open(LOG_CSV, "a", newline="") as f:
                    f.write(
                        f"{node_id},{latency_ms:.2f},{len(msg.payload)},{payload.get('battery_level',-1)},{payload.get('energy',0):.3f}\n"
                    )
            except Exception as e:
                print(f"[Gateway] Write CSV ERROR: {e}")

        if "enc_biometrics" in payload:
            enc_bytes = base64.b64decode(payload["enc_biometrics"])
            dec_start = time.time()
            vec = ts.bfv_vector_from(context, enc_bytes)
            decrypted_values = vec.decrypt()
            dec_time = time.time() - dec_start
            print(
                f"[Gateway] Received BATCH from Node {node_id} | Decryption Time: {dec_time:.4f} sec"
            )
            # print("before for i, val in enumerate(decrypted_values): ")
            for i, val in enumerate(decrypted_values):
                timestamp = payload["batch_timestamps"][i]
                hmac_expected = generate_hmac(f"{node_id}:{timestamp}:{val}")
                valid = hmac.compare_digest(payload["batch_HMAC"][i], hmac_expected)
                ref_val = trusted_database.get(node_id, [])
                if i < len(ref_val) and abs(ref_val[i] - val) < 1:
                    match_status = "MATCH"
                else:
                    match_status = "NO MATCH"
                # print(f"ref_val:{ref_val},difference:{abs(float(ref_val) - float(val))}")
                print(f"→ Biometric: {val} | HMAC: {valid} | Match: {match_status}")

        elif payload.get("type") == "light":
            biometric = payload["biometric"]
            timestamp = payload["timestamp"]
            hmac_expected = generate_hmac(f"{node_id}:{timestamp}:{biometric}")
            valid = hmac.compare_digest(payload["hmac"], hmac_expected)
            ref_val = trusted_database.get(node_id, [])
            match_status = (
                "MATCH" if ref_val and abs(ref_val[0] - biometric) < 1 else "NO MATCH"
            )
            print(
                f"[Gateway] Light AUTH from Node {node_id} | HMAC: {valid} | Match: {match_status}"
            )

        # if received_count >= expected_count:
        #     print(f"[Gateway] Received all {expected_count} messages. Stopping loop.")
        #     client.loop_stop()

    def is_fresh(node_id, ts):
        # Initialize deque for new node_ids
        # Replay Attack
        if node_id not in recent_timestamps:
            recent_timestamps[node_id] = deque()

        dq = recent_timestamps[node_id]
        now = time.time()

        # Convert timestamp to float if it's a string
        try:
            ts_float = float(ts) if ts is not None else now
        except (ValueError, TypeError):
            # If conversion fails, treat as current time
            ts_float = now

        # Convert REPLAY_WINDOW_SEC to float in case it's a string
        try:
            replay_window = float(REPLAY_WINDOW_SEC)
        except (ValueError, TypeError):
            replay_window = 60.0  # Default fallback

        # Remove old timestamps outside the replay window
        # Handle potential conversion errors for existing timestamps
        while dq:
            try:
                oldest_ts = float(dq[0])
                if now - oldest_ts > replay_window:
                    dq.popleft()
                else:
                    break
            except (ValueError, TypeError):
                # Remove invalid timestamp that can't be converted
                dq.popleft()

        # Check if timestamp already exists (replay attack)
        if ts_float in dq:
            return False

        # Add new timestamp
        dq.append(ts_float)
        return True

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
    # time.sleep((MSGS_PER_NODE + 5) * NUM_NODES)
    time.sleep(60)
    client.loop_stop()
    client.disconnect()




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/app/nodes/__init__.py =====
from .iot_node import *
from .gateway import gateway




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/app/nodes/gateway_underdev.py =====
import time
import hmac
import tenseal as ts
import paho.mqtt.client as mqtt
import json
import base64
import gzip

from collections import deque


from settings import (
    TOPIC,
    REPLAY_WINDOW_SEC,
    MQTT_PORT,
    MQTT_BROKER,
    MSGS_PER_NODE,
    NUM_NODES,
    LOG_CSV,
    MODE,
)
from ..core import generate_hmac


def gateway(context, trusted_database, recent_timestamps, dry_run=False):
    client = mqtt.Client()
    received_count = 0
    expected_count = NUM_NODES * MSGS_PER_NODE

    def on_connect(client, userdata, flags, rc):
        client.subscribe(TOPIC)

    def on_message(client, userdata, msg):
        nonlocal received_count
        try:
            if MODE == "Hybrid":
                compressed_payload = base64.b64decode(msg.payload)
                decompressed_json = gzip.decompress(compressed_payload).decode("utf-8")
                payload = json.loads(decompressed_json)
            else:
                payload = json.loads(msg.payload.decode("utf-8"))
        except (
            EOFError,
            gzip.BadGzipFile,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as e:
            print(f"[Gateway] Error in decompressing/parsing message: {e}")
            return  # Skip this corrupted or incomplete message
        receive_time_ns = time.time_ns()
        node_id = payload["node_id"]
        timestamp = (
            payload.get("timestamp") or payload.get("batch_timestamps", [None])[0]
        )
        if "enc_biometrics" in payload:
            base_latency = receive_time_ns - payload["batch_timestamps"][0] * 1e9
            latency_ms = base_latency / 1_000_000

        else:
            latency_ms = (receive_time_ns - payload["send_time_ns"]) / 1_000_000

        if not is_fresh(node_id, timestamp):
            print(f"[Gateway] Replay detected from Node {node_id}")
            return

        received_count += 1
        if not dry_run:
            try:
                with open(LOG_CSV, "a", newline="") as f:
                    f.write(
                        f"{node_id},{latency_ms:.2f},{len(msg.payload)},{payload.get('battery_level',-1)},{payload.get('energy',0):.3f}\n"
                    )
            except Exception as e:
                print(f"[Gateway] Write CSV ERROR: {e}")

        if "enc_biometrics" in payload:
            enc_bytes = base64.b64decode(payload["enc_biometrics"])
            dec_start = time.time()
            vec = ts.bfv_vector_from(context, enc_bytes)
            decrypted_values = vec.decrypt()
            dec_time = time.time() - dec_start
            print(
                f"[Gateway] Received BATCH from Node {node_id} | Decryption Time: {dec_time:.4f} sec"
            )

            for i, val in enumerate(decrypted_values):
                timestamp = payload["batch_timestamps"][i]
                hmac_expected = generate_hmac(f"{node_id}:{timestamp}:{val}")
                valid = hmac.compare_digest(payload["batch_HMAC"][i], hmac_expected)
                ref_val = trusted_database.get(node_id, None)
                match_status = (
                    "MATCH" if ref_val and abs(ref_val - val) < 100 else "NO MATCH"
                )
                print(f"→ Biometric: {val} | HMAC: {valid} | Match: {match_status}")
                print(f"[Gateway] {trusted_database}")
        elif payload.get("type") == "light":
            biometric = payload["biometric"]
            timestamp = payload["timestamp"]
            hmac_expected = generate_hmac(f"{node_id}:{timestamp}:{biometric}")
            valid = hmac.compare_digest(payload["hmac"], hmac_expected)
            ref_val = trusted_database.get(node_id, None)
            match_status = (
                "MATCH" if ref_val and abs(ref_val - biometric) < 100 else "NO MATCH"
            )
            print(
                f"[Gateway] Light AUTH from Node {node_id} | HMAC: {valid} | Match: {match_status}"
            )

        if received_count >= expected_count:
            print(f"[Gateway] Received all {expected_count} messages. Stopping loop.")
            client.loop_stop()

    def is_fresh(node_id, ts):
        # Initialize deque for new node_ids
        # Replay Attack
        if node_id not in recent_timestamps:
            recent_timestamps[node_id] = deque()

        dq = recent_timestamps[node_id]
        now = time.time()

        # Convert timestamp to float if it's a string
        try:
            ts_float = float(ts) if ts is not None else now
        except (ValueError, TypeError):
            # If conversion fails, treat as current time
            ts_float = now

        # Convert REPLAY_WINDOW_SEC to float in case it's a string
        try:
            replay_window = float(REPLAY_WINDOW_SEC)
        except (ValueError, TypeError):
            replay_window = 60.0  # Default fallback

        # Remove old timestamps outside the replay window
        # Handle potential conversion errors for existing timestamps
        while dq:
            try:
                oldest_ts = float(dq[0])
                if now - oldest_ts > replay_window:
                    dq.popleft()
                else:
                    break
            except (ValueError, TypeError):
                # Remove invalid timestamp that can't be converted
                dq.popleft()

        # Check if timestamp already exists (replay attack)
        if ts_float in dq:
            return False

        # Add new timestamp
        dq.append(ts_float)
        return True

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
    # time.sleep((MSGS_PER_NODE + 5) * NUM_NODES)
    # client.loop_stop()
    client.loop_forever()  # This will block and run until loop_stop() is called inside on_message
    client.disconnect()




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/app/nodes/iot_node/hybrid.py =====
import time
import tenseal as ts
import paho.mqtt.client as mqtt
import base64
import random

from settings import (
    MQTT_PORT,
    MQTT_BROKER,
    BATTERY_DEFAULT_VALUE,
    MSGS_PER_NODE,
    FHE_INTERVAL,
    BATTERY_THRESHOLD,
    ENERGY_PER_BYTE,
    TOPIC,
)

from ...core import generate_hmac
from ...utils import compress_data


def iot_node(
    node_id,
    context,
    lock,
    energy_consumption,
    mqtt_broker=None,
    mqtt_port=None,
    trusted_database=None,
):
    mqtt_broker = mqtt_broker or MQTT_BROKER
    mqtt_port = mqtt_port or MQTT_PORT
    client = mqtt.Client()
    client.connect(mqtt_broker, mqtt_port, 60)
    client.loop_start()

    battery_level = BATTERY_DEFAULT_VALUE
    batch_plain = []
    biometric_vector = trusted_database[node_id]

    for msg_count in range(1, MSGS_PER_NODE + 1):
        time.sleep(random.uniform(0.5, 2))

        if random.random() < 0.8:
            biometric_value = biometric_vector[(msg_count - 1) % len(biometric_vector)]
        else:
            biometric_value = round(
                random.uniform(0.1, 1.0), 6
            )  # simulate false biometric

        timestamp = round(time.time(), 3)
        message_light = f"{node_id}:{timestamp}:{biometric_value}"
        signature = generate_hmac(message_light)

        battery_level -= random.randint(1, 2)

        payload = None
        msg_bytes = None
        encoded_compressed = None

        if msg_count % FHE_INTERVAL == 0:
            batch_plain.append(
                {
                    "biometric": biometric_value,
                    "timestamp": timestamp,
                    "hmac": signature,
                }
            )
            enc_batch = [entry["biometric"] for entry in batch_plain]
            enc_vec = ts.bfv_vector(context, enc_batch)
            serialized_enc = base64.b64encode(enc_vec.serialize()).decode("utf-8")

            payload = {
                "node_id": node_id,
                "battery_level": battery_level,
                "batch_HMAC": [entry["hmac"] for entry in batch_plain],
                "batch_timestamps": [entry["timestamp"] for entry in batch_plain],
                "enc_biometrics": serialized_enc,
                "batch_size": len(batch_plain),
            }
            encoded_compressed = compress_data(payload)
            # msg_bytes = payload_str.encode('utf-8')
            msg_bytes = encoded_compressed.encode("utf-8")
            msg_energy = len(msg_bytes) * ENERGY_PER_BYTE
            payload["energy"] = msg_energy
            # Re-compress with energy included
            encoded_compressed = compress_data(payload)
            msg_bytes = encoded_compressed.encode("utf-8")
            print(
                f"[Node {node_id}] Sent BATCH with FHE ({len(batch_plain)} recs) | Energy: {msg_energy:.3f} mJ | Battery: {battery_level}"
            )
            batch_plain = []

        else:
            if battery_level < BATTERY_THRESHOLD:
                payload = {
                    "node_id": node_id,
                    "type": "light",
                    "battery_level": battery_level,
                    "hmac": signature,
                    "timestamp": timestamp,
                    "biometric": biometric_value,
                }
                encoded_compressed = compress_data(payload)
                # msg_bytes = payload_str.encode('utf-8')
                msg_bytes = encoded_compressed.encode("utf-8")
                msg_energy = len(msg_bytes) * ENERGY_PER_BYTE
                payload["energy"] = msg_energy
                # Re-compress with energy included
                encoded_compressed = compress_data(payload)
                msg_bytes = encoded_compressed.encode("utf-8")
                print(
                    f"[Node {node_id}] Sent ONLY HMAC (Battery Low) | Energy: {msg_energy:.3f} mJ | Battery: {battery_level}"
                )
            else:
                batch_plain.append(
                    {
                        "biometric": biometric_value,
                        "timestamp": timestamp,
                        "hmac": signature,
                    }
                )
                continue

        with lock:
            energy_consumption[node_id] += len(msg_bytes) * ENERGY_PER_BYTE

        send_time_ns = time.time_ns()
        payload["send_time_ns"] = send_time_ns
        # qos=1 ensures message delivery
        # client.publish(TOPIC, payload_str, qos=1)
        client.publish(TOPIC, encoded_compressed, qos=1)

    client.loop_stop()
    client.disconnect()




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/app/nodes/iot_node/__init__.py =====
from .plain import iot_node as plain_iot_node
from .hybrid import iot_node as hybrid_iot_node




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/app/nodes/iot_node/plain.py =====
import time
import tenseal as ts
import paho.mqtt.client as mqtt
import json
import base64
import random

from settings import (
    MQTT_PORT,
    MQTT_BROKER,
    MSGS_PER_NODE,
    ENERGY_PER_BYTE,
    TOPIC,
)

from ...core import generate_hmac


def iot_node(
    node_id, context, lock, energy_consumption, mqtt_broker=None, mqtt_port=None
):
    mqtt_broker = mqtt_broker or MQTT_BROKER
    mqtt_port = mqtt_port or MQTT_PORT
    client = mqtt.Client()
    client.connect(mqtt_broker, mqtt_port, 60)
    client.loop_start()

    for _ in range(MSGS_PER_NODE):
        time.sleep(random.uniform(0.5, 2))
        biometric_value = random.randint(1000, 9999)
        timestamp = round(time.time(), 3)
        message_light = f"{node_id}:{timestamp}:{biometric_value}"
        signature = generate_hmac(message_light)

        enc_vec = ts.bfv_vector(context, [biometric_value])
        serialized_enc = base64.b64encode(enc_vec.serialize()).decode("utf-8")

        payload = {
            "node_id": node_id,
            "battery_level": 100,
            "hmac": signature,
            "timestamp": timestamp,
            "enc_biometric": serialized_enc,
        }
        send_time_ns = time.time_ns()
        payload["send_time_ns"] = send_time_ns
        payload_str = json.dumps(payload)
        msg_bytes = payload_str.encode("utf-8")
        msg_energy = len(msg_bytes) * ENERGY_PER_BYTE
        payload["energy"] = msg_energy
        payload_str = json.dumps(payload)
        msg_bytes = payload_str.encode("utf-8")

        with lock:
            energy_consumption[node_id] += len(msg_bytes) * ENERGY_PER_BYTE

        print(f"[Node {node_id}] Sent FHE + HMAC | Energy: {msg_energy:.3f} mJ")
        client.publish(TOPIC, payload_str)

    client.loop_stop()
    client.disconnect()




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/app/utils/metrics.py =====
from settings import MODE, LOG_CSV


def create_output_csv(mode=None):
    _mode = mode or MODE
    _file = LOG_CSV
    with open(_file, "w", newline="") as f:
        f.write("node_id,latency_ms,bytes,battery,energy\n")




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/app/utils/plot.py =====
import pandas as pd
import numpy as np
import os
import glob
import matplotlib
import matplotlib.pyplot as plt

from settings import OUTPUT_FILE, MODE, OUTPUT_DIR, LOG_CSV, NUM_NODES, DRY_RUN

from .quadratic_regressoin import combined_cost

is_interactive = matplotlib.get_backend() in matplotlib.rcsetup.interactive_bk


def plot_energy_consumption(nodes, energy_values, dry_run=DRY_RUN):
    plt.figure(figsize=(8, 4))
    plt.bar(nodes, energy_values, color="purple")
    plt.xlabel("Node ID")
    plt.ylabel("Energy Consumed (mJ)")
    plt.title(
        f"Energy Consumption per Node - Adaptive Batching & Crypto (Nodes: {NUM_NODES})"
    )
    plt.grid(axis="y")
    plt.tight_layout()

    if not dry_run:
        # Save figure instead of showing it
        save_path = os.path.join(
            OUTPUT_DIR, f"plots/energy_consumption_nodes_{NUM_NODES}.png"
        )
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path)
        plt.close()


def plot_boxplot_latency(mode=None):
    _mode = mode or MODE
    _file = LOG_CSV
    df = pd.read_csv(_file)
    plt.figure(figsize=(8, 4))
    df.boxplot(column="latency_ms", by="node_id")
    plt.ylabel("Latency (ms)")
    plt.title(f"Boxplot Latency per Node (Nodes: {NUM_NODES})")
    plt.suptitle("")

    # Save figure instead of showing it
    save_path = os.path.join(OUTPUT_DIR, f"plots/latency_boxplot_nodes_{NUM_NODES}.png")
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path)
    plt.close()


def plot_latency_energy_vs_batch_size(
    batch_sizes, latencies=None, energies=None, bytes=None, alpha=1.0
):
    # ---- Fit polynomials for each metric ----
    latency_coeffs = np.polyfit(batch_sizes, latencies, deg=2)
    energy_coeffs = np.polyfit(batch_sizes, energies, deg=2)
    bytes_coeffs = np.polyfit(batch_sizes, bytes, deg=2)

    # ---- Evaluate combined cost ----
    combined_costs = [
        combined_cost(lat, en, alpha) for lat, en in zip(latencies, energies)
    ]

    # ---- Optimal batch sizes ----
    optimal_latency_batch = round(-latency_coeffs[1] / (2 * latency_coeffs[0]))
    optimal_latency = np.polyval(latency_coeffs, optimal_latency_batch)

    optimal_energy_batch = round(-energy_coeffs[1] / (2 * energy_coeffs[0]))
    optimal_energy = np.polyval(energy_coeffs, optimal_energy_batch)

    optimal_bytes_batch = round(-bytes_coeffs[1] / (2 * bytes_coeffs[0]))
    optimal_bytes = np.polyval(bytes_coeffs, optimal_bytes_batch)

    if optimal_latency_batch < 0:
        optimal_latency_batch = 0

    # ---- Create figure with multiple Y axes ----
    fig, ax1 = plt.subplots(figsize=(12, 6))

    # Latency plot
    color1 = "tab:blue"
    ax1.set_xlabel("Batch Size")
    ax1.set_ylabel("Latency (ms)", color=color1)
    l1 = ax1.plot(batch_sizes, latencies, color=color1, marker="o", label="Latency")
    ax1.tick_params(axis="y", labelcolor=color1)
    ax1.axvline(optimal_latency_batch, color=color1, linestyle="--", alpha=0.6)
    ax1.scatter([optimal_latency_batch], [optimal_latency], color=color1, s=80)

    # Energy plot
    ax2 = ax1.twinx()
    color2 = "tab:green"
    ax2.set_ylabel("Energy (mJ)", color=color2)
    l2 = ax2.plot(batch_sizes, energies, color=color2, marker="s", label="Energy")
    ax2.tick_params(axis="y", labelcolor=color2)
    ax2.axvline(optimal_energy_batch, color=color2, linestyle="--", alpha=0.6)
    ax2.scatter([optimal_energy_batch], [optimal_energy], color=color2, s=80)

    # Bytes plot (3rd Y axis)
    ax3 = ax1.twinx()
    color3 = "tab:red"
    ax3.spines["right"].set_position(("outward", 60))
    ax3.set_ylabel("Bytes Sent", color=color3)
    l3 = ax3.plot(batch_sizes, bytes, color=color3, marker="^", label="Bytes")
    ax3.tick_params(axis="y", labelcolor=color3)
    ax3.axvline(optimal_bytes_batch, color=color3, linestyle="--", alpha=0.6)
    ax3.scatter([optimal_bytes_batch], [optimal_bytes], color=color3, s=80)

    # Combined cost on ax1 (optional overlay)
    l4 = ax1.plot(
        batch_sizes,
        combined_costs,
        color="gray",
        linestyle="--",
        marker="x",
        label="Combined Cost",
    )

    # ---- Title and Legends ----
    plt.title("Latency, Energy, Bytes, and Combined Cost vs Batch Size")
    lines = l1 + l2 + l3 + l4
    labels = [line.get_label() for line in lines]
    ax1.legend(lines, labels, loc="upper left")
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def dynamic_node_visualization(node_states, data_flows, steps=100, interval=200):
    """
    node_states: list of dicts [{"id": int, "pos": (x, y), "state": int}]
    data_flows: list of tuples (from_id, to_id, active: bool)
    steps: number of animation frames
    interval: ms between frames
    """
    fig, ax = plt.subplots()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect("equal")

    # Assign colors for states
    state_colors = ["gray", "green", "red", "blue", "orange"]

    # Draw initial nodes
    scat = ax.scatter(
        [n["pos"][0] for n in node_states],
        [n["pos"][1] for n in node_states],
        c=[state_colors[n["state"] % len(state_colors)] for n in node_states],
        s=200,
        edgecolors="black",
    )

    # Draw initial flows (arrows)
    arrows = []
    for flow in data_flows:
        from_node = next(n for n in node_states if n["id"] == flow[0])
        to_node = next(n for n in node_states if n["id"] == flow[1])
        arr = ax.annotate(
            "",
            xy=to_node["pos"],
            xytext=from_node["pos"],
            arrowprops=dict(arrowstyle="->", color="cyan" if flow[2] else "gray", lw=2),
        )
        arrows.append(arr)

    def update(frame):
        # Example: randomly change states and flows for demo
        for n in node_states:
            n["state"] = np.random.randint(0, len(state_colors))
        scat.set_color(
            [state_colors[n["state"] % len(state_colors)] for n in node_states]
        )
        # Randomly activate/deactivate flows
        for i, flow in enumerate(data_flows):
            active = np.random.rand() > 0.5
            data_flows[i] = (flow[0], flow[1], active)
            arrows[i].arrow_patch.set_color("cyan" if active else "gray")
        return (scat,)

    # ani = animation.FuncAnimation(
    #     fig, update, frames=steps, interval=interval, blit=False
    # )
    plt.show()


def plot_batch_efficiency_summary(
    path=None,
):
    _csv_dir = path or f"{OUTPUT_DIR}/batch_efficiency_summary.csv"
    # Load your CSV file
    df = pd.read_csv(_csv_dir)
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, axes = plt.subplots(3, 1, figsize=(10, 12))

    # --- Latency plot ---
    axes[0].errorbar(
        df["batch_size"],
        df["avg_latency"],
        yerr=df["std_latency"],
        fmt="-o",
        capsize=4,
        label="Avg Latency",
    )
    axes[0].fill_between(
        df["batch_size"],
        df["min_latency"],
        df["max_latency"],
        alpha=0.2,
        label="Latency Range",
    )
    axes[0].set_title("Latency vs Batch Size")
    axes[0].set_xlabel("Batch Size")
    axes[0].set_ylabel("Latency (ms)")
    axes[0].legend()

    # --- Energy plot ---
    axes[1].errorbar(
        df["batch_size"],
        df["total_energy"],
        yerr=df["std_energy"],
        fmt="-s",
        capsize=4,
        color="green",
        label="Avg Energy",
    )
    axes[1].fill_between(
        df["batch_size"],
        df["min_energy"],
        df["max_energy"],
        alpha=0.2,
        color="green",
        label="Energy Range",
    )
    axes[1].set_title("Energy Consumption vs Batch Size")
    axes[1].set_xlabel("Batch Size")
    axes[1].set_ylabel("Energy (J)")
    axes[1].legend()

    # --- Battery and Node Count plot ---
    ax2 = axes[2].twinx()
    axes[2].plot(
        df["batch_size"], df["avg_battery"], "-^", label="Avg Battery (%)", color="blue"
    )
    ax2.plot(
        df["batch_size"], df["node_count"], "--o", label="Node Count", color="orange"
    )
    axes[2].set_title("Battery and Node Count vs Batch Size")
    axes[2].set_xlabel("Batch Size")
    axes[2].set_ylabel("Battery (%)")
    ax2.set_ylabel("Node Count")

    axes[2].legend(loc="upper left")
    ax2.legend(loc="upper right")

    plt.tight_layout()
    plt.show()


def load_batch_data_from_csvs(csv_directory=None, dry_run=False):
    """
    Load data from multiple CSV files generated by batch runs.

    Args:
        csv_directory: Directory containing CSV files. If None, uses OUTPUT_DIR/logs
        dry_run (bool, optional): If True, runs analysis without executing plotting or file writes.


    Returns:
        dict: Dictionary with batch_size as key and DataFrame as value
    """
    if csv_directory is None:
        csv_directory = os.path.join(OUTPUT_DIR, "logs")

    # Find all CSV files from batch runs
    csv_pattern = os.path.join(csv_directory, "metrics_log_Hybrid_10_*_*_*_20.csv")
    csv_files = glob.glob(csv_pattern)

    batch_data = {}

    for csv_file in csv_files:
        try:
            # Extract FHE_INTERVAL from filename
            filename = os.path.basename(csv_file)
            parts = filename.replace(".csv", "").split("_")

            if len(parts) >= 7:
                fhe_interval = int(parts[-2])  # FHE_INTERVAL is second to last

                # Read CSV data
                df = pd.read_csv(csv_file)
                df["batch_size"] = fhe_interval  # Add batch size column
                batch_data[fhe_interval] = df

                print(f"Loaded batch {fhe_interval}: {len(df)} nodes")

        except Exception as e:
            print(f"Error processing {csv_file}: {e}")

    return batch_data


def analyze_batch_efficiency(batch_data, dry_run=False):
    """
    Analyze energy and latency efficiency across batch sizes.

    Args:
        batch_data: Dictionary from load_batch_data_from_csvs()
        dry_run (bool, optional): If True, runs analysis without executing plotting or file writes.


    Returns:
        tuple: (summary_df, optimal_energy_batch, optimal_latency_batch)
    """
    summary_data = []

    for batch_size in sorted(batch_data.keys()):
        df = batch_data[batch_size]
        energy_sum_by_node = df.groupby("node_id")["energy"].sum()
        latency_sum_by_node = df.groupby("node_id")["latency_ms"].sum()
        battrey_sum_by_node = df.groupby("node_id")["battery"].sum()
        # Calculate statistics for this batch
        stats = {
            "batch_size": batch_size,
            # "avg_latency": df["latency_ms"].mean(),
            "avg_latency": latency_sum_by_node.mean(),
            "std_latency": df["latency_ms"].std(),
            "min_latency": df["latency_ms"].min(),
            "max_latency": df["latency_ms"].max(),
            # "avg_energy": df["energy"].mean(),
            "avg_energy": energy_sum_by_node.mean(),
            "std_energy": df["energy"].std(),
            "min_energy": df["energy"].min(),
            "max_energy": df["energy"].max(),
            "total_energy": df["energy"].sum(),
            # "avg_battery": df["battery"].mean(),
            "avg_battery": battrey_sum_by_node.mean(),
            "min_battery": df["battery"].min(),
            "node_count": len(df),
        }
        summary_data.append(stats)

    summary_df = pd.DataFrame(summary_data)

    # Find optimal batch sizes
    optimal_energy_batch = summary_df.loc[
        summary_df["avg_energy"].idxmin(), "batch_size"
    ]
    optimal_latency_batch = summary_df.loc[
        summary_df["avg_latency"].idxmin(), "batch_size"
    ]

    return summary_df, optimal_energy_batch, optimal_latency_batch


def plot_comprehensive_batch_analysis(
    batch_data=None, csv_directory=None, save_plots=True, dry_run=False
):
    """
    Create comprehensive plots showing energy and latency analysis across batch sizes.

    Args:
        batch_data: Pre-loaded batch data. If None, loads from csv_directory
        csv_directory: Directory containing CSV files
        save_plots: Whether to save plots to files
        dry_run (bool, optional): If True, runs analysis without executing plotting or file writes.

    """
    # Load data if not provided
    if batch_data is None:
        batch_data = load_batch_data_from_csvs(csv_directory)

    if not batch_data:
        print("No batch data found!")
        return

    if dry_run:
        save_plots = False
    # Analyze efficiency
    summary_df, optimal_energy_batch, optimal_latency_batch = analyze_batch_efficiency(
        batch_data
    )

    print(f"\n=== BATCH EFFICIENCY ANALYSIS ===")
    print(f"Optimal batch size for ENERGY efficiency: {optimal_energy_batch}")
    print(f"Optimal batch size for LATENCY efficiency: {optimal_latency_batch}")
    print(
        f"Energy at optimal batch: {summary_df[summary_df['batch_size']==optimal_energy_batch]['avg_energy'].iloc[0]:.3f} mJ"
    )
    print(
        f"Latency at optimal batch: {summary_df[summary_df['batch_size']==optimal_latency_batch]['avg_latency'].iloc[0]:.2f} ms"
    )

    # Create plots directory
    if save_plots:
        plots_dir = os.path.join(OUTPUT_DIR, "plots")
        os.makedirs(plots_dir, exist_ok=True)

    # Check if we're in an interactive backend
    is_interactive = matplotlib.get_backend() in matplotlib.rcsetup.interactive_bk

    # ============ PLOT 1: Individual Node Performance by Batch Size ============
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12))

    # Energy consumption per node
    batch_sizes = sorted(batch_data.keys())
    colors = plt.cm.viridis(np.linspace(0, 1, len(batch_sizes)))

    for i, batch_size in enumerate(batch_sizes):
        df = batch_data[batch_size]
        ax1.scatter(
            [batch_size] * len(df),
            df["energy"],
            alpha=0.6,
            color=colors[i],
            s=50,
            label=f"Batch {batch_size}",
        )

    # Add average line
    ax1.plot(
        batch_sizes,
        summary_df["avg_energy"],
        linewidth=2,
        markersize=8,
        label="Average Energy",
        color="red",
        marker="o",
    )

    # Mark optimal point
    # ax1.axvline(
    #     x=optimal_energy_batch,
    #     color="green",
    #     linestyle="--",
    #     linewidth=2,
    #     label=f"Optimal Energy (Batch {optimal_energy_batch})",
    # )

    ax1.set_xlabel("Batch Size (FHE Interval)")
    ax1.set_ylabel("Energy Consumption (mJ)")
    ax1.set_title("Energy Consumption per Node Across Batch Sizes")
    ax1.grid(True, alpha=0.3)
    ax1.legend(bbox_to_anchor=(1.05, 1), loc="upper left")

    # Latency per node
    for i, batch_size in enumerate(batch_sizes):
        df = batch_data[batch_size]
        ax2.scatter(
            [batch_size] * len(df), df["latency_ms"], alpha=0.6, color=colors[i], s=50
        )

    # Add average line
    ax2.plot(
        batch_sizes,
        summary_df["avg_latency"],
        linewidth=2,
        markersize=8,
        label="Average Latency",
        color="blue",
        marker="o",
    )

    # Mark optimal point
    # ax2.axvline(
    #     x=optimal_latency_batch,
    #     color="orange",
    #     linestyle="--",
    #     linewidth=2,
    #     label=f"Optimal Latency (Batch {optimal_latency_batch})",
    # )

    ax2.set_xlabel("Batch Size (FHE Interval)")
    ax2.set_ylabel("Latency (ms)")
    ax2.set_title("Latency per Node Across Batch Sizes")
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    plt.tight_layout()
    if save_plots:
        plt.savefig(
            os.path.join(
                plots_dir, f"individual_node_performance_{NUM_NODES}nodes.png"
            ),
            dpi=300,
            bbox_inches="tight",
        )
        plt.close(fig)
    elif is_interactive:
        plt.show()

    # ============ PLOT 2: Summary Statistics with Error Bars ============
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    # Energy efficiency plot
    ax1.errorbar(
        summary_df["batch_size"],
        summary_df["avg_energy"],
        yerr=summary_df["std_energy"],
        fmt="o-",
        capsize=5,
        capthick=2,
        color="purple",
        linewidth=2,
        markersize=8,
    )
    ax1.fill_between(
        summary_df["batch_size"],
        summary_df["avg_energy"] - summary_df["std_energy"],
        summary_df["avg_energy"] + summary_df["std_energy"],
        alpha=0.2,
        color="purple",
    )

    # Mark optimal point
    # optimal_energy_row = summary_df[
    #     summary_df["batch_size"] == optimal_energy_batch
    # ].iloc[0]
    # ax1.scatter(
    #     [optimal_energy_batch],
    #     [optimal_energy_row["avg_energy"]],
    #     color="green",
    #     s=150,
    #     marker="*",
    #     zorder=5,
    #     label=f"Optimal: Batch {optimal_energy_batch}",
    # )

    ax1.set_xlabel("Batch Size (FHE Interval)")
    ax1.set_ylabel("Average Energy Consumption (mJ)")
    ax1.set_title("Energy Efficiency Analysis")
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    # Latency efficiency plot
    ax2.errorbar(
        summary_df["batch_size"],
        summary_df["avg_latency"],
        yerr=summary_df["std_latency"],
        fmt="o-",
        capsize=5,
        capthick=2,
        color="blue",
        linewidth=2,
        markersize=8,
    )
    ax2.fill_between(
        summary_df["batch_size"],
        summary_df["avg_latency"] - summary_df["std_latency"],
        summary_df["avg_latency"] + summary_df["std_latency"],
        alpha=0.2,
        color="blue",
    )

    # Mark optimal point
    # optimal_latency_row = summary_df[
    #     summary_df["batch_size"] == optimal_latency_batch
    # ].iloc[0]
    # ax2.scatter(
    #     [optimal_latency_batch],
    #     [optimal_latency_row["avg_latency"]],
    #     color="orange",
    #     s=150,
    #     marker="*",
    #     zorder=5,
    #     label=f"Optimal: Batch {optimal_latency_batch}",
    # )

    ax2.set_xlabel("Batch Size (FHE Interval)")
    ax2.set_ylabel("Average Latency (ms)")
    ax2.set_title("Latency Efficiency Analysis")
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    plt.tight_layout()
    if save_plots:
        plt.savefig(
            os.path.join(plots_dir, f"efficiency_analysis_{NUM_NODES}nodes.png"),
            dpi=300,
            bbox_inches="tight",
        )
        plt.close(fig)
    elif is_interactive:
        plt.show()

    # ============ PLOT 3: Combined Efficiency Trade-off ============
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))

    # Normalize metrics for comparison (0-1 scale)
    norm_energy = (summary_df["avg_energy"] - summary_df["avg_energy"].min()) / (
        summary_df["avg_energy"].max() - summary_df["avg_energy"].min()
    )
    norm_latency = (summary_df["avg_latency"] - summary_df["avg_latency"].min()) / (
        summary_df["avg_latency"].max() - summary_df["avg_latency"].min()
    )

    # Plot normalized metrics
    ax.plot(
        summary_df["batch_size"],
        norm_energy,
        "o-",
        linewidth=3,
        markersize=8,
        color="purple",
        label="Normalized Energy",
    )
    ax.plot(
        summary_df["batch_size"],
        norm_latency,
        "s-",
        linewidth=3,
        markersize=8,
        color="blue",
        label="Normalized Latency",
    )

    # Combined score (equal weights)
    combined_score = (norm_energy + norm_latency) / 2
    ax.plot(
        summary_df["batch_size"],
        combined_score,
        "^-",
        linewidth=3,
        markersize=8,
        color="red",
        label="Combined Score",
    )

    # Find optimal combined point
    # optimal_combined_batch = summary_df.loc[combined_score.idxmin(), "batch_size"]
    # ax.axvline(
    #     x=optimal_combined_batch,
    #     color="red",
    #     linestyle="--",
    #     linewidth=2,
    #     label=f"Optimal Combined (Batch {optimal_combined_batch})",
    # )

    # Mark individual optimal points
    # ax.axvline(
    #     x=optimal_energy_batch,
    #     color="purple",
    #     linestyle=":",
    #     alpha=0.7,
    #     label=f"Energy Optimal (Batch {optimal_energy_batch})",
    # )
    # ax.axvline(
    #     x=optimal_latency_batch,
    #     color="blue",
    #     linestyle=":",
    #     alpha=0.7,
    #     label=f"Latency Optimal (Batch {optimal_latency_batch})",
    # )

    ax.set_xlabel("Batch Size (FHE Interval)")
    ax.set_ylabel("Normalized Score (0=Best, 1=Worst)")
    ax.set_title("Combined Efficiency Trade-off Analysis")
    ax.grid(True, alpha=0.3)
    ax.legend()
    ax.set_ylim(-0.05, 1.05)

    plt.tight_layout()
    if save_plots:
        plt.savefig(
            os.path.join(plots_dir, f"combined_tradeoff_{NUM_NODES}nodes.png"),
            dpi=300,
            bbox_inches="tight",
        )
        plt.close(fig)
    elif is_interactive:
        plt.show()

    # ============ PLOT 4: Battery Impact Analysis ============
    fig, ax = plt.subplots(1, 1, figsize=(12, 6))

    # Box plot of battery levels by batch size
    battery_by_batch = [batch_data[batch]["battery"].values for batch in batch_sizes]

    # Use tick_labels instead of labels to avoid deprecation warning
    box_plot = ax.boxplot(battery_by_batch, tick_labels=batch_sizes, patch_artist=True)

    # Color the boxes
    colors = plt.cm.RdYlGn(np.linspace(0.2, 0.8, len(batch_sizes)))
    for patch, color in zip(box_plot["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)

    ax.set_xlabel("Batch Size (FHE Interval)")
    ax.set_ylabel("Battery Level (%)")
    ax.set_title("Battery Levels Distribution by Batch Size")
    ax.grid(True, alpha=0.3)

    # Add horizontal line at battery threshold (if available)
    ax.axhline(y=20, color="red", linestyle="--", alpha=0.7, label="Battery Threshold")
    ax.legend()

    plt.tight_layout()
    if save_plots:
        plt.savefig(
            os.path.join(plots_dir, f"battery_analysis_{NUM_NODES}nodes.png"),
            dpi=300,
            bbox_inches="tight",
        )
        plt.close(fig)
    elif is_interactive:
        plt.show()

    # ============ SAVE SUMMARY DATA ============
    if save_plots:
        summary_file = os.path.join(OUTPUT_DIR, "batch_efficiency_summary.csv")
        summary_df.to_csv(summary_file, index=False)
        print(f"\nSummary data saved to: {summary_file}")

    # Print detailed summary
    print(f"\n=== DETAILED EFFICIENCY SUMMARY ===")
    print(summary_df.round(3))

    return summary_df, optimal_energy_batch, optimal_latency_batch


# Convenience function to run the analysis
def run_batch_analysis(csv_directory: str = None, dry_run: bool = False):
    """
    Main function to run the complete batch analysis.

    Args:
        csv_directory: Directory containing CSV files. If None, uses OUTPUT_DIR/logs
        dry_run (bool, optional): If True, runs analysis without executing plotting or file writes.


    Returns:
        tuple: (summary_df, optimal_energy_batch, optimal_latency_batch)
    """
    print("Starting comprehensive batch analysis...")
    return plot_comprehensive_batch_analysis(
        csv_directory=csv_directory, dry_run=dry_run
    )


def setup_plot_latency_energy_vs_batch_size_data(
    batch_size_from: int,
    batch_size_to: int,
    nodes_number: int = 10,
) -> tuple[list[int], list[float], list[float], list[float]]:

    _directory = f"{OUTPUT_DIR}/logs"
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

    return _batch_sizes, _latencies, _energies, _bytes


# def plot_latency_energy_vs_batch_size(batch_sizes, latencies, energies, alpha=1.0):
#     """
#     Plots latency, energy, and combined cost vs batch size.
#     Auto-detects optimal batch sizes empirically within the data range.
#     """
#
#     # Ensure data is in NumPy format
#     batch_sizes = np.array(batch_sizes)
#     latencies = np.array(latencies)
#     energies = np.array(energies)
#
#     # Combined cost (e.g. weighted latency + energy)
#     combined_costs = latencies + alpha * energies
#
#     # Empirical minima
#     optimal_latency_batch = batch_sizes[np.argmin(latencies)]
#     optimal_latency = latencies[np.argmin(latencies)]
#
#     optimal_energy_batch = batch_sizes[np.argmin(energies)]
#     optimal_energy = energies[np.argmin(energies)]
#
#     optimal_combined_batch = batch_sizes[np.argmin(combined_costs)]
#     optimal_combined_cost = combined_costs[np.argmin(combined_costs)]
#
#     if optimal_latency_batch < 0:
#         optimal_latency_batch = 0
#
#     # ---- 2D Plot ----
#     fig1 = plt.figure(figsize=(10, 6))
#     plt.plot(batch_sizes, latencies, marker="o", label="Latency (ms)", color="blue")
#     plt.plot(batch_sizes, energies, marker="s", label="Energy (mJ)", color="purple")
#     plt.plot(
#         batch_sizes, combined_costs, marker="^", label="Combined Cost", color="green"
#     )
#
#     # Show optimal points
#     plt.axvline(
#         x=optimal_latency_batch,
#         color="blue",
#         linestyle="--",
#         label=f"Opt Latency: {optimal_latency_batch}",
#     )
#     plt.axvline(
#         x=optimal_energy_batch,
#         color="purple",
#         linestyle="--",
#         label=f"Opt Energy: {optimal_energy_batch}",
#     )
#     plt.scatter([optimal_latency_batch], [optimal_latency], color="blue", s=80)
#     plt.scatter([optimal_energy_batch], [optimal_energy], color="purple", s=80)
#
#     plt.title("Latency, Energy, and Combined Cost vs Batch Size")
#     plt.xlabel("Batch Size")
#     plt.ylabel("Value")
#     plt.grid(True)
#     plt.legend()
#     plt.tight_layout()
#
#     # Save figure instead of showing it
#     save_path = os.path.join(
#         OUTPUT_DIR, f"plots/combined_metrics_nodes_{NUM_NODES}.png"
#     )
#     os.makedirs(os.path.dirname(save_path), exist_ok=True)
#     plt.savefig(save_path)
#     plt.close()
#
#     # ---- 3D Plot ----
#     fig2 = plt.figure(figsize=(10, 7))
#     ax = fig2.add_subplot(111, projection="3d")
#     ax.plot(
#         batch_sizes,
#         latencies,
#         zs=0,
#         zdir="z",
#         label="Latency",
#         color="blue",
#         marker="o",
#     )
#     ax.plot(
#         batch_sizes, energies, zs=0, zdir="y", label="Energy", color="green", marker="^"
#     )
#
#     ax.set_xlabel("Batch Size")
#     ax.set_ylabel("Latency (ms)")
#     ax.set_zlabel("Energy (mJ)")
#     ax.set_title("3D Plot: Latency and Energy vs Batch Size")
#     ax.legend()
#     plt.tight_layout()
#
#     # Save figure instead of showing it
#     save_path = os.path.join(OUTPUT_DIR, f"plots/3d_plot1_nodes_{NUM_NODES}.png")
#     os.makedirs(os.path.dirname(save_path), exist_ok=True)
#     plt.savefig(save_path)
#     plt.close()
#
#     fig2 = plt.figure(figsize=(10, 7))
#     ax = fig2.add_subplot(111, projection="3d")
#     ax.plot(
#         batch_sizes,
#         latencies,
#         zs=0,
#         zdir="z",
#         label="Latency",
#         color="blue",
#         marker="o",
#     )
#     ax.plot(
#         batch_sizes, energies, zs=0, zdir="y", label="Energy", color="green", marker="^"
#     )
#
#     ax.set_xlabel("Batch Size")
#     ax.set_ylabel("Latency (ms)")
#     ax.set_zlabel("Energy (mJ)")
#     ax.set_title("3D Plot of Latency and Energy vs Batch Size")
#     ax.legend()
#
#     # Save figure instead of showing it
#     save_path = os.path.join(OUTPUT_DIR, f"plots/3d_plot2_nodes_{NUM_NODES}.png")
#     os.makedirs(os.path.dirname(save_path), exist_ok=True)
#     plt.savefig(save_path)
#     plt.close()




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/app/utils/__init__.py =====
from .plot import (
    plot_energy_consumption,
    plot_boxplot_latency,
    plot_latency_energy_vs_batch_size,
    plot_batch_efficiency_summary,
    plot_comprehensive_batch_analysis,
    setup_plot_latency_energy_vs_batch_size_data,
    analyze_batch_efficiency,
    run_batch_analysis,
    load_batch_data_from_csvs,
)
from .metrics import create_output_csv
from .compress import compress_data
from .parser import parse_arguments
from .quadratic_regressoin import (
    estimate_latency,
    estimate_energy,
    estimate_combined_cost,
)




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/app/utils/parser.py =====
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




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/app/utils/setup.py =====
import pandas as pd

from settings import OUTPUT_DIR
from app.utils.plot import plot_latency_energy_vs_batch_size


def setup_plot_latency_energy_vs_batch_size_data(batch_size: int):
    directory = f"{OUTPUT_DIR}/logs/"
    _batch_sizes = []
    _latencies = []
    _energies = []

    for b in range(1, batch_size + 1):
        file_name = f"metrics_log_Hybrid_10_15_0.001_{b}_20.csv"
        file_path = directory + file_name
        df = pd.read_csv(file_path)
        _batch_sizes.append(b)
        energy_sum_by_node = df.groupby("node_id")["energy"].sum()
        mean_of_node_sums_energy = energy_sum_by_node.mean()
        latency_sum_by_node = df.groupby("node_id")["latency_ms"].sum()
        mean_of_node_sums_latency = latency_sum_by_node.mean()
        _latencies.append(float(mean_of_node_sums_latency))
        _energies.append(float(mean_of_node_sums_energy))

    return _batch_sizes, _latencies, _energies


if __name__ == "__main__":
    batch_sizes, latencies, energies = setup_plot_latency_energy_vs_batch_size_data(
        batch_size=10
    )
    plot_latency_energy_vs_batch_size(
        batch_sizes=batch_sizes,
        latencies=latencies,
        energies=energies,
    )




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/app/utils/plot_executer.py =====
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




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/app/utils/compress.py =====
import base64
import json
import gzip


def compress_data(payload: dict) -> str:
    payload_str = json.dumps(payload)
    compressed = gzip.compress(payload_str.encode("utf-8"))
    return base64.b64encode(compressed).decode("utf-8")




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/app/utils/quadratic_regressoin.py =====
import numpy as np
import matplotlib.pyplot as plt
from numpy.polynomial.polynomial import Polynomial
from mpl_toolkits.mplot3d import Axes3D


# تخمین تأخیر بر اساس مدل درجه دوم
def estimate_latency(batch_size):
    return round(136.34 * batch_size**2 + 308.83 * batch_size + 1102.12, 2)


# تخمین انرژی بر اساس مدل درجه دوم
def estimate_energy(batch_size):
    return round(25.16 * batch_size**2 - 380.18 * batch_size + 1475.66, 2)


# تابع هزینه ترکیبی: latency + alpha * energy
def estimate_combined_cost(batch_size, alpha=1.0):
    return estimate_latency(batch_size) + alpha * estimate_energy(batch_size)


def combined_cost(lat, en, alpha=1.0):
    return alpha * lat + (1 - alpha) * en


"""
batch_sizes = np.arange(1, 16)
latencies = [estimate_latency(b) for b in batch_sizes]
energies = [estimate_energy(b) for b in batch_sizes]
combined_costs = [estimate_combined_cost(b, alpha=1.0) for b in batch_sizes]
"""




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/archive/__init__.py =====




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/archive/output/logs/__init__.py =====




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/archive/codes/hybrid_leightweight_homomorphic_somewhat.py =====
import simpy
import random
import hashlib
import hmac
import tenseal as ts

NUM_NODES = 10
SIM_TIME = 100
ENERGY_PER_BYTE = 0.001
SHARED_SECRET = b"my_shared_secret_key"

# تنظیم رمزنگاری Somewhat Homomorphic Encryption با پارامترهای سبک‌تر
# (مثلاً poly_modulus_degree کمتر و plain_modulus مناسب)
context = ts.context(
    ts.SCHEME_TYPE.BFV, poly_modulus_degree=4096, plain_modulus=1032193
)
context.generate_galois_keys()
context.generate_relin_keys()
context.global_scale = 2**40

total_energy_consumed_she = {node: 0.0 for node in range(NUM_NODES)}
total_latency_she = []

trusted_database = {i: i * 1000 + 1234 for i in range(NUM_NODES)}


def iot_node_she(env, node_id, gateway_pipe):
    while True:
        yield env.timeout(random.randint(20, 40))  # فرکانس ارسال کاهش یافته
        biometric_value = random.randint(1000, 9999)

        # مرحله سبک‌وزن: ارسال اطلاعات هویت و امضای HMAC
        message = f"{node_id}:{env.now}"
        signature = hmac.new(
            SHARED_SECRET, message.encode(), hashlib.sha256
        ).hexdigest()
        packet_light = f"{message}:{signature}"
        size_light = len(packet_light.encode("utf-8"))
        energy_light = size_light * ENERGY_PER_BYTE

        # مرحله رمزنگاری Somewhat: فقط رمزنگاری بخشی از داده (مثلاً فقط بیت‌های کم اهمیت‌تر)
        # برای سادگی، فرض می‌کنیم فقط نصف داده رمزنگاری شود (مثال مفهومی)
        partial_value = biometric_value // 2
        enc_vec = ts.bfv_vector(context, [partial_value])
        serialized_enc = enc_vec.serialize()
        size_she = len(serialized_enc)
        energy_she = size_she * ENERGY_PER_BYTE

        total_energy_consumed_she[node_id] += energy_light + energy_she

        print(
            f"[Time {env.now}] Node {node_id} sends lightweight + Somewhat HE data | Energy used: {energy_light + energy_she:.3f} mJ"
        )
        yield gateway_pipe.put(
            (env.now, node_id, packet_light, serialized_enc, biometric_value)
        )


def gateway_she(env, gateway_pipe):
    while True:
        (
            timestamp,
            sender,
            packet_light,
            serialized_enc,
            original_value,
        ) = yield gateway_pipe.get()
        latency = env.now - timestamp
        total_latency_she.append(latency)

        # اعتبارسنجی HMAC
        try:
            parts = packet_light.split(":")
            node_id = int(parts[0])
            sent_time = float(parts[1])
            signature = parts[2]
            message = f"{node_id}:{sent_time}"
            expected_signature = hmac.new(
                SHARED_SECRET, message.encode(), hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(signature, expected_signature):
                print(f"[Time {env.now}] Invalid HMAC signature from Node {sender}")
                continue
        except:
            print(
                f"[Time {env.now}] Error parsing lightweight message from Node {sender}"
            )
            continue

        # پردازش رمزنگاری Somewhat
        enc_vec = ts.bfv_vector_from(context, serialized_enc)
        decrypted_partial = enc_vec.decrypt()[0]

        # بازسازی مقدار اصلی (مثلاً با تقریب)
        reconstructed_value = decrypted_partial * 2  # فرض ساده برای بازسازی

        # مقایسه با مقدار مرجع
        ref_val = trusted_database.get(node_id, None)
        match_status = (
            "MATCH" if abs(ref_val - reconstructed_value) < 100 else "NO MATCH"
        )

        print(
            f"[Time {env.now}] Gateway authenticates Node {sender} (Latency: {latency}s) → {match_status}"
        )


env = simpy.Environment()
gateway_pipe = simpy.Store(env)

for node in range(NUM_NODES):
    env.process(iot_node_she(env, node, gateway_pipe))

env.process(gateway_she(env, gateway_pipe))

env.run(until=SIM_TIME)

print("\n--- Somewhat Homomorphic Encryption Hybrid Simulation Summary ---")
for node, energy in total_energy_consumed_she.items():
    print(f"Node {node}: {energy:.2f} mJ")
avg_latency = (
    sum(total_latency_she) / len(total_latency_she) if total_latency_she else 0
)
print(f"Average Latency: {avg_latency:.2f} seconds")




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/archive/codes/hybrid_leightweight_homomorphic.py =====
import simpy
import random
import hashlib
import hmac
import tenseal as ts

NUM_NODES = 10
SIM_TIME = 100
ENERGY_PER_BYTE = 0.001
SHARED_SECRET = b"my_shared_secret_key"

# تنظیم رمزنگاری BFV
context = ts.context(
    ts.SCHEME_TYPE.BFV, poly_modulus_degree=4096, plain_modulus=1032193
)
context.generate_galois_keys()
context.generate_relin_keys()
context.global_scale = 2**40

total_energy_consumed_hybrid = {node: 0.0 for node in range(NUM_NODES)}
total_latency_hybrid = []

trusted_database = {i: i * 1000 + 1234 for i in range(NUM_NODES)}


def iot_node_hybrid(env, node_id, gateway_pipe):
    while True:
        yield env.timeout(random.randint(50, 100))
        biometric_value = random.randint(1000, 9999)
        # مرحله سبک‌وزن: تولید پیام HMAC
        message = f"{node_id}:{biometric_value}:{env.now}"
        signature = hmac.new(
            SHARED_SECRET, message.encode(), hashlib.sha256
        ).hexdigest()
        packet_light = f"{message}:{signature}"
        size_light = len(packet_light.encode("utf-8"))
        energy_light = size_light * ENERGY_PER_BYTE
        total_energy_consumed_hybrid[node_id] += energy_light

        # مرحله رمزنگاری همومورفیک روی داده حساس (مثلاً فقط مقدار بیومتریک)
        enc_vec = ts.bfv_vector(context, [biometric_value])
        serialized_enc = enc_vec.serialize()
        size_he = len(serialized_enc)
        energy_he = size_he * ENERGY_PER_BYTE
        total_energy_consumed_hybrid[node_id] += energy_he

        print(
            f"[Time {env.now}] Node {node_id} sends lightweight + HE data | Energy used: {energy_light + energy_he:.3f} mJ"
        )
        yield gateway_pipe.put((env.now, node_id, packet_light, serialized_enc))


def gateway_hybrid(env, gateway_pipe):
    while True:
        timestamp, sender, packet_light, serialized_enc = yield gateway_pipe.get()
        latency = env.now - timestamp
        total_latency_hybrid.append(latency)

        # اعتبارسنجی HMAC
        try:
            parts = packet_light.split(":")
            node_id = int(parts[0])
            biometric = int(parts[1])
            sent_time = float(parts[2])
            signature = parts[3]
            message = f"{node_id}:{biometric}:{sent_time}"
            expected_signature = hmac.new(
                SHARED_SECRET, message.encode(), hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(signature, expected_signature):
                print(f"[Time {env.now}] Invalid HMAC signature from Node {sender}")
                continue
        except:
            print(
                f"[Time {env.now}] Error parsing lightweight message from Node {sender}"
            )
            continue

        # پردازش رمزنگاری همومورفیک
        enc_vec = ts.bfv_vector_from(context, serialized_enc)
        ref_val = trusted_database.get(node_id, None)
        ref_enc = ts.bfv_vector(context, [ref_val])
        diff = enc_vec - ref_enc
        decrypted = diff.decrypt()[0]
        match_status = "MATCH" if decrypted == 0 else "NO MATCH"
        print(
            f"[Time {env.now}] Gateway authenticates Node {sender} (Latency: {latency}s) → {match_status}"
        )


env = simpy.Environment()
gateway_pipe = simpy.Store(env)

for node in range(NUM_NODES):
    env.process(iot_node_hybrid(env, node, gateway_pipe))

env.process(gateway_hybrid(env, gateway_pipe))

env.run(until=SIM_TIME)

print("\n--- Hybrid Simulation Summary ---")
for node, energy in total_energy_consumed_hybrid.items():
    print(f"Node {node}: {energy:.2f} mJ")
avg_latency = (
    sum(total_latency_hybrid) / len(total_latency_hybrid) if total_latency_hybrid else 0
)
print(f"Average Latency: {avg_latency:.2f} seconds")




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/archive/codes/pandas.py =====
import pandas as pd
import matplotlib.pyplot as plt

from .Hybrid_2_with_new_changes import OUTPUT_FILE

df = pd.read_csv()
plt.figure(figsize=(8, 4))
df.boxplot(column="latency_ms", by="node_id")
plt.ylabel("Latency (ms)")
plt.title("Boxplot Latency per Node")
plt.suptitle("")
plt.show()




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/archive/codes/hybrid_(leightweight@Homomorphic)wiht_MQTT.py =====
import time
import hmac
import hashlib
import tenseal as ts
import paho.mqtt.client as mqtt
import json
import threading
import base64
import random
import matplotlib.pyplot as plt

# ---------- تنظیمات ----------
NUM_NODES = 3  # تعداد نودها
MSGS_PER_NODE = 10  # پیام برای هر نود
ENERGY_PER_BYTE = 0.001  # میلی ژول به ازای هر بایت
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
TOPIC = "iot/biometric"
SHARED_SECRET = b"my_shared_secret_key"

context = ts.context(
    ts.SCHEME_TYPE.BFV, poly_modulus_degree=8192, plain_modulus=1032193
)
context.generate_galois_keys()
context.generate_relin_keys()
context.global_scale = 2**40

# ---------- متغیرها ----------
energy_consumption = {node: 0.0 for node in range(NUM_NODES)}
lock = threading.Lock()  # برای همگام‌سازی دسترسی به متغیر مشترک انرژی

# ---------- HMAC ----------
def generate_hmac(message: str) -> str:
    return hmac.new(SHARED_SECRET, message.encode(), hashlib.sha256).hexdigest()


# ---------- IOT NODE ----------
def iot_node(node_id):
    client = mqtt.Client()
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
    for _ in range(MSGS_PER_NODE):
        time.sleep(1 + node_id)  # زمان ارسال متنوع برای هریک
        biometric_value = random.randint(1000, 9999)
        enc_vec = ts.bfv_vector(context, [biometric_value])
        serialized_enc = enc_vec.serialize()
        timestamp = time.time()
        message_light = f"{node_id}:{timestamp}"
        signature = generate_hmac(message_light)
        payload = {
            "node_id": node_id,
            "timestamp": timestamp,
            "hmac": signature,
            "enc_biometric": base64.b64encode(serialized_enc).decode("utf-8"),
        }
        payload_str = json.dumps(payload)
        msg_bytes = payload_str.encode("utf-8")
        # هر پیام خروجی نسبت به حجم، مصرف انرژی دارد
        with lock:
            energy_consumption[node_id] += len(msg_bytes) * ENERGY_PER_BYTE
        print(
            f"[Node {node_id}] Energy for this msg: {len(msg_bytes)*ENERGY_PER_BYTE:.3f} mJ, Total: {energy_consumption[node_id]:.3f} mJ"
        )
        client.publish(TOPIC, payload_str)
    client.loop_stop()
    client.disconnect()


# ---------- GATEWAY ----------
def gateway():
    client = mqtt.Client()

    def on_connect(client, userdata, flags, rc):
        print("[Gateway] Connected.")
        client.subscribe(TOPIC)

    def on_message(client, userdata, msg):
        # فرایند عادی اعتبارسنجی و رمزگشایی
        pass  # بدنه این بخش قبلاً دارید و روی انرژی تاثیر ندارد.

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
    time.sleep((MSGS_PER_NODE + 2) * NUM_NODES)  # زمان کافی برای دریافت همه پیام‌ها
    client.loop_stop()
    client.disconnect()


# ---------- اجرا ----------
if __name__ == "__main__":
    threads = []
    gw_thread = threading.Thread(target=gateway)
    gw_thread.start()
    threads.append(gw_thread)
    for node_id in range(NUM_NODES):
        t = threading.Thread(target=iot_node, args=(node_id,))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()

    # ----- رسم نمودار -----
    nodes = list(energy_consumption.keys())
    energy_values = list(energy_consumption.values())
    print("\nTotal Energy Consumption (mJ):")
    for node, energy in energy_consumption.items():
        print(f"Node {node}: {energy:.2f} mJ")
    plt.figure(figsize=(8, 4))
    plt.bar(nodes, energy_values, color="orange")
    plt.xlabel("Node ID")
    plt.ylabel("Energy Consumed (mJ)")
    plt.title("Energy Consumption per IoT Node (Homomorphic + MQTT)")
    plt.grid(axis="y")
    plt.tight_layout()
    plt.show()




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/archive/codes/Hybrid_2.py =====
import time
import hmac
import hashlib
import tenseal as ts
import paho.mqtt.client as mqtt
import json
import threading
import base64
import random
import matplotlib.pyplot as plt

NUM_NODES = 10
MSGS_PER_NODE = 15
ENERGY_PER_BYTE = 0.001
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
TOPIC = "iot/biometric"
SHARED_SECRET = b"my_shared_secret_key"
FHE_INTERVAL = 5
BATTERY_THRESHOLD = 20
BATTERY_DEFAULT_VALUE = 100

context = ts.context(
    ts.SCHEME_TYPE.BFV, poly_modulus_degree=4096, plain_modulus=1032193
)
context.generate_galois_keys()
context.generate_relin_keys()
context.global_scale = 2**40

energy_consumption = {node: 0.0 for node in range(NUM_NODES)}
lock = threading.Lock()
trusted_database = {i: i * 1000 + 1234 for i in range(NUM_NODES)}


def generate_hmac(message: str) -> str:
    return hmac.new(SHARED_SECRET, message.encode(), hashlib.sha256).hexdigest()


def iot_node(node_id):
    client = mqtt.Client()
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()

    battery_level = BATTERY_DEFAULT_VALUE
    batch_plain = []

    for msg_count in range(1, MSGS_PER_NODE + 1):
        time.sleep(random.uniform(0.5, 2))
        biometric_value = random.randint(1000, 9999)
        timestamp = time.time()
        message_light = f"{node_id}:{timestamp}:{biometric_value}"
        signature = generate_hmac(message_light)

        battery_level -= random.randint(1, 2)

        payload = None
        msg_bytes = None

        if msg_count % FHE_INTERVAL == 0:
            batch_plain.append(
                {
                    "biometric": biometric_value,
                    "timestamp": timestamp,
                    "hmac": signature,
                }
            )
            enc_batch = [entry["biometric"] for entry in batch_plain]
            enc_vec = ts.bfv_vector(context, enc_batch)
            serialized_enc = base64.b64encode(enc_vec.serialize()).decode("utf-8")

            payload = {
                "node_id": node_id,
                "battery_level": battery_level,
                "batch_HMAC": [entry["hmac"] for entry in batch_plain],
                "batch_timestamps": [entry["timestamp"] for entry in batch_plain],
                "enc_biometrics": serialized_enc,
                "batch_size": len(batch_plain),
            }
            payload_str = json.dumps(payload)
            msg_bytes = payload_str.encode("utf-8")
            print(
                f"[Node {node_id}] Sent BATCH with FHE ({len(batch_plain)} recs) | Energy: {len(msg_bytes)*ENERGY_PER_BYTE:.3f} mJ | Battery: {battery_level}"
            )
            batch_plain = []

        else:
            if battery_level < BATTERY_THRESHOLD:
                payload = {
                    "node_id": node_id,
                    "type": "light",
                    "battery_level": battery_level,
                    "hmac": signature,
                    "timestamp": timestamp,
                    "biometric": biometric_value,
                }
                payload_str = json.dumps(payload)
                msg_bytes = payload_str.encode("utf-8")
                print(
                    f"[Node {node_id}] Sent ONLY HMAC (Battery Low) | Energy: {len(msg_bytes)*ENERGY_PER_BYTE:.3f} mJ | Battery: {battery_level}"
                )
            else:
                batch_plain.append(
                    {
                        "biometric": biometric_value,
                        "timestamp": timestamp,
                        "hmac": signature,
                    }
                )
                continue

        with lock:
            energy_consumption[node_id] += len(msg_bytes) * ENERGY_PER_BYTE

        client.publish(TOPIC, payload_str)

    client.loop_stop()
    client.disconnect()


def gateway():
    client = mqtt.Client()

    def on_connect(client, userdata, flags, rc):
        client.subscribe(TOPIC)

    def on_message(client, userdata, msg):
        payload = json.loads(msg.payload.decode("utf-8"))
        node_id = payload["node_id"]

        if "enc_biometrics" in payload:
            enc_bytes = base64.b64decode(payload["enc_biometrics"])
            dec_start = time.time()
            vec = ts.bfv_vector_from(context, enc_bytes)
            decrypted_values = vec.decrypt()
            dec_time = time.time() - dec_start
            print(
                f"[Gateway] Received BATCH from Node {node_id} | Decryption Time: {dec_time:.4f} sec"
            )

            for i, val in enumerate(decrypted_values):
                timestamp = payload["batch_timestamps"][i]
                hmac_expected = generate_hmac(f"{node_id}:{timestamp}:{val}")
                valid = hmac.compare_digest(payload["batch_HMAC"][i], hmac_expected)
                ref_val = trusted_database.get(node_id, None)
                match_status = (
                    "MATCH" if ref_val and abs(ref_val - val) < 100 else "NO MATCH"
                )
                print(f"→ Biometric: {val} | HMAC: {valid} | Match: {match_status}")

        elif payload.get("type") == "light":
            biometric = payload["biometric"]
            timestamp = payload["timestamp"]
            hmac_expected = generate_hmac(f"{node_id}:{timestamp}:{biometric}")
            valid = hmac.compare_digest(payload["hmac"], hmac_expected)
            ref_val = trusted_database.get(node_id, None)
            match_status = (
                "MATCH" if ref_val and abs(ref_val - biometric) < 100 else "NO MATCH"
            )
            print(
                f"[Gateway] Light AUTH from Node {node_id} | HMAC: {valid} | Match: {match_status}"
            )

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
    time.sleep((MSGS_PER_NODE + 5) * NUM_NODES)
    client.loop_stop()
    client.disconnect()


if __name__ == "__main__":
    threads = []

    gw_thread = threading.Thread(target=gateway)
    gw_thread.start()
    threads.append(gw_thread)

    for node_id in range(NUM_NODES):
        t = threading.Thread(target=iot_node, args=(node_id,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    nodes = list(energy_consumption.keys())
    energy_values = list(energy_consumption.values())
    print("\nTotal Energy Consumption (mJ):")
    for node, energy in energy_consumption.items():
        print(f"Node {node}: {energy:.2f} mJ")
    plt.figure(figsize=(8, 4))
    plt.bar(nodes, energy_values, color="purple")
    plt.xlabel("Node ID")
    plt.ylabel("Energy Consumed (mJ)")
    plt.title("Energy Consumption per Node - Adaptive Batching & Crypto")
    plt.grid(axis="y")
    plt.tight_layout()
    plt.show()




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/archive/codes/jwt_simulation.py =====
import simpy
import random
import jwt  # pip install PyJWT
import time
import matplotlib.pyplot as plt

# پارامترهای عمومی
NUM_NODES = 10
SIM_TIME = 100
ENERGY_PER_BYTE = 0.001  # میلی ژول به ازای هر بایت انتقال داده
SECRET_KEY = "my_secret_key"  # کلید مخفی برای امضای JWT

# آمار مصرف انرژی و تأخیر
total_energy_consumed_jwt = {node: 0.0 for node in range(NUM_NODES)}
total_latency_jwt = []

# تابع تولید داده و ارسال JWT
def iot_node_jwt(env, node_id, gateway_pipe):
    while True:
        yield env.timeout(random.randint(5, 15))
        biometric_value = random.randint(1000, 9999)
        payload = {
            "node_id": node_id,
            "biometric": biometric_value,
            "timestamp": env.now,
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
        data_size = len(token.encode("utf-8"))
        energy = data_size * ENERGY_PER_BYTE
        total_energy_consumed_jwt[node_id] += energy
        print(
            f"[Time {env.now}] Node {node_id} sends JWT token to Gateway | Biometric: {biometric_value} | Energy used: {energy:.3f} mJ"
        )
        yield gateway_pipe.put((env.now, node_id, token))


# تابع دریافت و اعتبارسنجی JWT در Gateway
trusted_database = {i: i * 1000 + 1234 for i in range(NUM_NODES)}


def gateway_jwt(env, gateway_pipe):
    while True:
        timestamp, sender, token = yield gateway_pipe.get()
        latency = env.now - timestamp
        total_latency_jwt.append(latency)
        try:
            decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            ref_val = trusted_database.get(decoded["node_id"], None)
            match_status = "MATCH" if ref_val == decoded["biometric"] else "NO MATCH"
        except jwt.InvalidTokenError:
            match_status = "INVALID TOKEN"
        print(
            f"[Time {env.now}] Gateway received JWT from Node {sender} (Latency: {latency}s) → Authentication: {match_status}"
        )


# شبیه‌سازی
env = simpy.Environment()
gateway_pipe = simpy.Store(env)

for node in range(NUM_NODES):
    env.process(iot_node_jwt(env, node, gateway_pipe))

env.process(gateway_jwt(env, gateway_pipe))

env.run(until=SIM_TIME)

# خروجی نهایی
print("\n--- JWT Simulation Summary ---")
print("Total Energy Consumed (mJ):")
for node, energy in total_energy_consumed_jwt.items():
    print(f"Node {node}: {energy:.2f} mJ")

avg_latency = (
    sum(total_latency_jwt) / len(total_latency_jwt) if total_latency_jwt else 0
)
print(f"\nAverage Latency: {avg_latency:.2f} seconds")

# نمودار مصرف انرژی
nodes = list(total_energy_consumed_jwt.keys())
energy_values = list(total_energy_consumed_jwt.values())

plt.figure(figsize=(10, 5))
plt.bar(nodes, energy_values, color="orange")
plt.xlabel("Node ID")
plt.ylabel("Energy Consumed (mJ)")
plt.title("Energy Consumption per IoT Node (JWT)")
plt.grid(True)
plt.tight_layout()
plt.show()




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/archive/codes/leightweight_auth.py =====
import simpy
import random
import hashlib
import hmac
import matplotlib.pyplot as plt

# پارامترهای عمومی
NUM_NODES = 10
SIM_TIME = 100
ENERGY_PER_BYTE = 0.001  # میلی ژول به ازای هر بایت انتقال داده
SHARED_SECRET = b"my_shared_secret_key"  # کلید مشترک برای HMAC

# آمار مصرف انرژی و تأخیر
total_energy_consumed_light = {node: 0.0 for node in range(NUM_NODES)}
total_latency_light = []

# تابع تولید داده و ارسال پیام احراز هویت سبک‌وزن
def iot_node_light(env, node_id, gateway_pipe):
    while True:
        yield env.timeout(random.randint(50, 100))
        biometric_value = random.randint(1000, 9999)
        message = f"{node_id}:{biometric_value}:{env.now}"
        # تولید کد HMAC به عنوان امضای پیام
        signature = hmac.new(
            SHARED_SECRET, message.encode(), hashlib.sha256
        ).hexdigest()
        packet = f"{message}:{signature}"
        data_size = len(packet.encode("utf-8"))
        energy = data_size * ENERGY_PER_BYTE
        total_energy_consumed_light[node_id] += energy
        print(
            f"[Time {env.now}] Node {node_id} sends lightweight auth message to Gateway | Biometric: {biometric_value} | Energy used: {energy:.3f} mJ"
        )
        yield gateway_pipe.put((env.now, node_id, packet))


# تابع دریافت و اعتبارسنجی پیام در Gateway
trusted_database = {i: i * 1000 + 1234 for i in range(NUM_NODES)}


def gateway_light(env, gateway_pipe):
    while True:
        timestamp, sender, packet = yield gateway_pipe.get()
        latency = env.now - timestamp
        total_latency_light.append(latency)
        try:
            parts = packet.split(":")
            node_id = int(parts[0])
            biometric = int(parts[1])
            sent_time = float(parts[2])
            signature = parts[3]
            message = f"{node_id}:{biometric}:{sent_time}"
            # اعتبارسنجی HMAC
            expected_signature = hmac.new(
                SHARED_SECRET, message.encode(), hashlib.sha256
            ).hexdigest()
            if hmac.compare_digest(signature, expected_signature):
                ref_val = trusted_database.get(node_id, None)
                match_status = "MATCH" if ref_val == biometric else "NO MATCH"
            else:
                match_status = "INVALID SIGNATURE"
        except Exception as e:
            match_status = "ERROR"
        print(
            f"[Time {env.now}] Gateway received lightweight auth from Node {sender} (Latency: {latency}s) → Authentication: {match_status}"
        )


# شبیه‌سازی
env = simpy.Environment()
gateway_pipe = simpy.Store(env)

for node in range(NUM_NODES):
    env.process(iot_node_light(env, node, gateway_pipe))

env.process(gateway_light(env, gateway_pipe))

env.run(until=SIM_TIME)

# خروجی نهایی
print("\n--- Lightweight Auth Simulation Summary ---")
print("Total Energy Consumed (mJ):")
for node, energy in total_energy_consumed_light.items():
    print(f"Node {node}: {energy:.2f} mJ")

avg_latency = (
    sum(total_latency_light) / len(total_latency_light) if total_latency_light else 0
)
print(f"\nAverage Latency: {avg_latency:.2f} seconds")

# نمودار مصرف انرژی
nodes = list(total_energy_consumed_light.keys())
energy_values = list(total_energy_consumed_light.values())

plt.figure(figsize=(10, 5))
plt.bar(nodes, energy_values, color="green")
plt.xlabel("Node ID")
plt.ylabel("Energy Consumed (mJ)")
plt.title("Energy Consumption per IoT Node (Lightweight Auth)")
plt.grid(True)
plt.tight_layout()
plt.show()




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/archive/codes/Hybrid_1.py =====
import time
import hmac
import hashlib
import tenseal as ts
import paho.mqtt.client as mqtt
import json
import threading
import base64
import random
import matplotlib.pyplot as plt

NUM_NODES = 10
MSGS_PER_NODE = 15
ENERGY_PER_BYTE = 0.001
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
TOPIC = "iot/biometric"
SHARED_SECRET = b"my_shared_secret_key"
FHE_INTERVAL = 5  # هر ۵ پیام یکبار FHE
BATTERY_THRESHOLD = 20  # اگر باتری کمتر از ۲۰ درصد شد، فقط HMAC

"""
	•	هر ۵ پیام یکبار رمزنگاری FHE بر کل batch:‌ حجم را کاهش می‌دهد و انرژی جمعی کمتر مصرف می‌شود.
	•	در صورت پایین بودن باتری، به‌صورت تطبیقی فقط HMAC ارسال می‌شود، الگوریتم همچنان batchهای ۵تایی را رعایت می‌کند.
	•	در دفعات دیگر اطلاعات batch شده فقط ذخیره می‌شوند، و ارسال نمی‌شوند تا batch کامل شود.
	•	مصرف انرژی هر پیام براساس اندازه بایت محاسبه و جمع می‌شود.
	•	نمودار مصرف انرژی برای هر نود رسم می‌شود.
"""

context = ts.context(
    ts.SCHEME_TYPE.BFV, poly_modulus_degree=4096, plain_modulus=1032193
)
context.generate_galois_keys()
context.generate_relin_keys()
context.global_scale = 2**40

energy_consumption = {node: 0.0 for node in range(NUM_NODES)}
lock = threading.Lock()


def generate_hmac(message: str) -> str:
    return hmac.new(SHARED_SECRET, message.encode(), hashlib.sha256).hexdigest()


def iot_node(node_id):
    client = mqtt.Client()
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()

    battery_level = 20  # باتری را ۱۰۰ درصد شروع می‌کنیم
    batch_plain = []
    fhe_counter = 0

    for msg_count in range(1, MSGS_PER_NODE + 1):
        time.sleep(random.uniform(0.5, 2))  # فاصله زمانی هر ارسال
        biometric_value = random.randint(1000, 9999)
        timestamp = time.time()
        message_light = f"{node_id}:{timestamp}:{biometric_value}"
        signature = generate_hmac(message_light)

        # کاستن باتری طبق یک مدل ساده: هر پیام ۱ یا ۲ درصد مصرف
        battery_level -= random.randint(1, 2)

        payload = None
        msg_bytes = None

        # رفتار batching adaptive:
        if msg_count % FHE_INTERVAL == 0:
            # اگر باتری پایین هم باشد هر ۵ بار باید FHE ارسال شود
            batch_plain.append(
                {
                    "biometric": biometric_value,
                    "timestamp": timestamp,
                    "hmac": signature,
                }
            )
            # پیام‌های batch شده را رمزنگاری و یکجا ارسال کن
            enc_batch = [entry["biometric"] for entry in batch_plain]
            enc_vec = ts.bfv_vector(context, enc_batch)
            serialized_enc = base64.b64encode(enc_vec.serialize()).decode("utf-8")

            payload = {
                "node_id": node_id,
                "battery_level": battery_level,
                "batch_HMAC": [entry["hmac"] for entry in batch_plain],
                "batch_timestamps": [entry["timestamp"] for entry in batch_plain],
                "enc_biometrics": serialized_enc,
                "batch_size": len(batch_plain),
            }
            payload_str = json.dumps(payload)
            msg_bytes = payload_str.encode("utf-8")
            print(
                f"[Node {node_id}] Sent BATCH with FHE ({len(batch_plain)} recs) | Energy: {len(msg_bytes)*ENERGY_PER_BYTE:.3f} mJ | Battery: {battery_level}"
            )
            batch_plain = []  # بعد ارسال batch بافر را خالی کن

        else:
            # اگر باتری کمتر از آستانه باشد فقط HMAC (بدون رمزنگاری FHE)
            if battery_level < BATTERY_THRESHOLD:
                payload = {
                    "node_id": node_id,
                    "type": "light",
                    "battery_level": battery_level,
                    "hmac": signature,
                    "timestamp": timestamp,
                    "biometric": biometric_value,
                }
                payload_str = json.dumps(payload)
                msg_bytes = payload_str.encode("utf-8")
                print(
                    f"[Node {node_id}] Sent ONLY HMAC (Battery Low) | Energy: {len(msg_bytes)*ENERGY_PER_BYTE:.3f} mJ | Battery: {battery_level}"
                )

            else:
                # هر پیام عادی هم برای batching نگه می‌داریم، ولی نمی‌فرستیم تا به مضرب FHE_INTERVAL برسیم
                batch_plain.append(
                    {
                        "biometric": biometric_value,
                        "timestamp": timestamp,
                        "hmac": signature,
                    }
                )
                continue  # چیزی ارسال نشود تا batch کامل شود

        with lock:
            energy_consumption[node_id] += len(msg_bytes) * ENERGY_PER_BYTE

        client.publish(TOPIC, payload_str)

    client.loop_stop()
    client.disconnect()


def gateway():
    client = mqtt.Client()

    def on_connect(client, userdata, flags, rc):
        client.subscribe(TOPIC)

    def on_message(client, userdata, msg):
        # پیاده‌سازی کامل برای سرور در این مثال حذف شده (مطابق با قبلی عمل شود)
        pass

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
    time.sleep((MSGS_PER_NODE + 5) * NUM_NODES)
    client.loop_stop()
    client.disconnect()


if __name__ == "__main__":
    threads = []

    gw_thread = threading.Thread(target=gateway)
    gw_thread.start()
    threads.append(gw_thread)

    for node_id in range(NUM_NODES):
        t = threading.Thread(target=iot_node, args=(node_id,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    # نمودار انرژی
    nodes = list(energy_consumption.keys())
    energy_values = list(energy_consumption.values())
    print("\nTotal Energy Consumption (mJ):")
    for node, energy in energy_consumption.items():
        print(f"Node {node}: {energy:.2f} mJ")
    plt.figure(figsize=(8, 4))
    plt.bar(nodes, energy_values, color="purple")
    plt.xlabel("Node ID")
    plt.ylabel("Energy Consumed (mJ)")
    plt.title("Energy Consumption per Node - Adaptive Batching & Crypto")
    plt.grid(axis="y")
    plt.tight_layout()
    plt.show()




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/archive/codes/Hybrid_2_with_new_changes.py =====
import time
import hmac
import hashlib
import tenseal as ts
import paho.mqtt.client as mqtt
import json
import threading
import base64
import random
import matplotlib.pyplot as plt
from collections import defaultdict, deque

NUM_NODES = 50
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

context = ts.context(
    ts.SCHEME_TYPE.BFV, poly_modulus_degree=POLY_MOD_DEGREE, plain_modulus=1032193
)
context.generate_galois_keys()
context.generate_relin_keys()
context.global_scale = 2**40

energy_consumption = {node: 0.0 for node in range(NUM_NODES)}
recent_timestamps = defaultdict(lambda: deque(maxlen=100))
with open(OUTPUT_FILE, "w", newline="") as f:
    f.write("node_id,latency_ms,bytes,battery\n")

lock = threading.Lock()
trusted_database = {i: i * 1000 + 1234 for i in range(NUM_NODES)}


def generate_hmac(message: str) -> str:
    return hmac.new(SHARED_SECRET, message.encode(), hashlib.sha256).hexdigest()


def iot_node(node_id):
    client = mqtt.Client()
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()

    battery_level = BATTERY_DEFAULT_VALUE
    batch_plain = []

    for msg_count in range(1, MSGS_PER_NODE + 1):
        time.sleep(random.uniform(0.5, 2))
        biometric_value = random.randint(1000, 9999)
        timestamp = time.time()
        message_light = f"{node_id}:{timestamp}:{biometric_value}"
        signature = generate_hmac(message_light)

        battery_level -= random.randint(1, 2)

        payload = None
        msg_bytes = None

        if msg_count % FHE_INTERVAL == 0:
            batch_plain.append(
                {
                    "biometric": biometric_value,
                    "timestamp": timestamp,
                    "hmac": signature,
                }
            )
            enc_batch = [entry["biometric"] for entry in batch_plain]
            enc_vec = ts.bfv_vector(context, enc_batch)
            serialized_enc = base64.b64encode(enc_vec.serialize()).decode("utf-8")

            payload = {
                "node_id": node_id,
                "battery_level": battery_level,
                "batch_HMAC": [entry["hmac"] for entry in batch_plain],
                "batch_timestamps": [entry["timestamp"] for entry in batch_plain],
                "enc_biometrics": serialized_enc,
                "batch_size": len(batch_plain),
            }
            payload_str = json.dumps(payload)
            msg_bytes = payload_str.encode("utf-8")
            print(
                f"[Node {node_id}] Sent BATCH with FHE ({len(batch_plain)} recs) | Energy: {len(msg_bytes)*ENERGY_PER_BYTE:.3f} mJ | Battery: {battery_level}"
            )
            batch_plain = []

        else:
            if battery_level < BATTERY_THRESHOLD:
                payload = {
                    "node_id": node_id,
                    "type": "light",
                    "battery_level": battery_level,
                    "hmac": signature,
                    "timestamp": timestamp,
                    "biometric": biometric_value,
                }
                payload_str = json.dumps(payload)
                msg_bytes = payload_str.encode("utf-8")
                print(
                    f"[Node {node_id}] Sent ONLY HMAC (Battery Low) | Energy: {len(msg_bytes)*ENERGY_PER_BYTE:.3f} mJ | Battery: {battery_level}"
                )
            else:
                batch_plain.append(
                    {
                        "biometric": biometric_value,
                        "timestamp": timestamp,
                        "hmac": signature,
                    }
                )
                continue

        with lock:
            energy_consumption[node_id] += len(msg_bytes) * ENERGY_PER_BYTE

        send_time_ns = time.time_ns()  # زمان دقیق نانوثانیه
        payload["send_time_ns"] = send_time_ns
        payload_str = json.dumps(payload)
        msg_bytes = payload_str.encode("utf-8")
        # qos=1 ensures message delivery
        client.publish(TOPIC, payload_str, qos=1)

    client.loop_stop()
    client.disconnect()


def gateway():
    client = mqtt.Client()

    def on_connect(client, userdata, flags, rc):
        client.subscribe(TOPIC)

    def on_message(client, userdata, msg):
        payload = json.loads(msg.payload.decode("utf-8"))
        receive_time_ns = time.time_ns()
        node_id = payload["node_id"]

        if "enc_biometrics" in payload:
            base_latency = (
                receive_time_ns - payload["batch_timestamps"][0] * 1e9
            )  # اولین رکورد
            latency_ms = base_latency / 1_000_000
        else:
            latency_ms = (receive_time_ns - payload["send_time_ns"]) / 1_000_000

        try:
            with open(OUTPUT_FILE, "a", newline="") as f:
                f.write(
                    f"{node_id},{latency_ms:.2f},{len(msg.payload)},{payload.get('battery_level',-1)}\n"
                )
        except Exception as e:
            print(f"[Gateway] Write CSV ERROR: {e}")

        # if not is_fresh(node_id, timestamp):
        #     print(f"[Gateway] Replay detected from Node {node_id}")
        #     return

        if "enc_biometrics" in payload:
            enc_bytes = base64.b64decode(payload["enc_biometrics"])
            dec_start = time.time()
            vec = ts.bfv_vector_from(context, enc_bytes)
            decrypted_values = vec.decrypt()
            dec_time = time.time() - dec_start
            print(
                f"[Gateway] Received BATCH from Node {node_id} | Decryption Time: {dec_time:.4f} sec"
            )

            for i, val in enumerate(decrypted_values):
                timestamp = payload["batch_timestamps"][i]
                hmac_expected = generate_hmac(f"{node_id}:{timestamp}:{val}")
                valid = hmac.compare_digest(payload["batch_HMAC"][i], hmac_expected)
                ref_val = trusted_database.get(node_id, None)
                match_status = (
                    "MATCH" if ref_val and abs(ref_val - val) < 100 else "NO MATCH"
                )
                print(f"→ Biometric: {val} | HMAC: {valid} | Match: {match_status}")

        elif payload.get("type") == "light":
            biometric = payload["biometric"]
            timestamp = payload["timestamp"]
            hmac_expected = generate_hmac(f"{node_id}:{timestamp}:{biometric}")
            valid = hmac.compare_digest(payload["hmac"], hmac_expected)
            ref_val = trusted_database.get(node_id, None)
            match_status = (
                "MATCH" if ref_val and abs(ref_val - biometric) < 100 else "NO MATCH"
            )
            print(
                f"[Gateway] Light AUTH from Node {node_id} | HMAC: {valid} | Match: {match_status}"
            )

    def is_fresh(node_id, ts):
        dq = recent_timestamps[node_id]
        now = time.time()
        while dq and now - dq[0] > REPLAY_WINDOW_SEC:
            dq.popleft()
        if ts in dq:
            return False
        dq.append(ts)
        return True

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
    time.sleep((MSGS_PER_NODE + 5) * NUM_NODES)
    client.loop_stop()
    client.disconnect()


if __name__ == "__main__":
    threads = []

    gw_thread = threading.Thread(target=gateway)
    gw_thread.start()
    threads.append(gw_thread)

    for node_id in range(NUM_NODES):
        t = threading.Thread(target=iot_node, args=(node_id,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    nodes = list(energy_consumption.keys())
    energy_values = list(energy_consumption.values())
    print("\nTotal Energy Consumption (mJ):")
    for node, energy in energy_consumption.items():
        print(f"Node {node}: {energy:.2f} mJ")
    plt.figure(figsize=(8, 4))
    plt.bar(nodes, energy_values, color="purple")
    plt.xlabel("Node ID")
    plt.ylabel("Energy Consumed (mJ)")
    plt.title("Energy Consumption per Node - Adaptive Batching & Crypto")
    plt.grid(axis="y")
    plt.tight_layout()
    plt.show()




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/archive/codes/homomorphic_without_approaches.py =====
import time
import hmac
import hashlib
import tenseal as ts
import paho.mqtt.client as mqtt
import json
import threading
import base64
import random
import matplotlib.pyplot as plt

NUM_NODES = 10
MSGS_PER_NODE = 15
ENERGY_PER_BYTE = 0.001
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
TOPIC = "iot/biometric"
SHARED_SECRET = b"my_shared_secret_key"

context = ts.context(
    ts.SCHEME_TYPE.BFV, poly_modulus_degree=4096, plain_modulus=1032193
)
context.generate_galois_keys()
context.generate_relin_keys()
context.global_scale = 2**40

energy_consumption = {node: 0.0 for node in range(NUM_NODES)}
lock = threading.Lock()
trusted_database = {i: i * 1000 + 1234 for i in range(NUM_NODES)}


def generate_hmac(message: str) -> str:
    return hmac.new(SHARED_SECRET, message.encode(), hashlib.sha256).hexdigest()


def iot_node(node_id):
    client = mqtt.Client()
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()

    for _ in range(MSGS_PER_NODE):
        time.sleep(random.uniform(0.5, 2))
        biometric_value = random.randint(1000, 9999)
        timestamp = time.time()
        message_light = f"{node_id}:{timestamp}:{biometric_value}"
        signature = generate_hmac(message_light)

        enc_vec = ts.bfv_vector(context, [biometric_value])
        serialized_enc = base64.b64encode(enc_vec.serialize()).decode("utf-8")

        payload = {
            "node_id": node_id,
            "battery_level": 100,  # ثابت چون adaptive نیست
            "hmac": signature,
            "timestamp": timestamp,
            "enc_biometric": serialized_enc,
        }
        payload_str = json.dumps(payload)
        msg_bytes = payload_str.encode("utf-8")

        with lock:
            energy_consumption[node_id] += len(msg_bytes) * ENERGY_PER_BYTE

        print(
            f"[Node {node_id}] Sent FHE + HMAC | Energy: {len(msg_bytes)*ENERGY_PER_BYTE:.3f} mJ"
        )
        client.publish(TOPIC, payload_str)

    client.loop_stop()
    client.disconnect()


def gateway():
    client = mqtt.Client()

    def on_connect(client, userdata, flags, rc):
        client.subscribe(TOPIC)

    def on_message(client, userdata, msg):
        payload = json.loads(msg.payload.decode("utf-8"))
        node_id = payload["node_id"]
        timestamp = payload["timestamp"]
        enc_bytes = base64.b64decode(payload["enc_biometric"])

        dec_start = time.time()
        vec = ts.bfv_vector_from(context, enc_bytes)
        decrypted_val = vec.decrypt()[0]
        dec_time = time.time() - dec_start

        hmac_expected = generate_hmac(f"{node_id}:{timestamp}:{decrypted_val}")
        valid = hmac.compare_digest(payload["hmac"], hmac_expected)
        ref_val = trusted_database.get(node_id, None)
        match_status = (
            "MATCH" if ref_val and abs(ref_val - decrypted_val) < 100 else "NO MATCH"
        )

        print(
            f"[Gateway] FHE AUTH from Node {node_id} | Biometric: {decrypted_val} | HMAC: {valid} | Match: {match_status} | Decrypt Time: {dec_time:.4f} sec"
        )

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
    time.sleep((MSGS_PER_NODE + 5) * NUM_NODES)
    client.loop_stop()
    client.disconnect()


if __name__ == "__main__":
    threads = []

    gw_thread = threading.Thread(target=gateway)
    gw_thread.start()
    threads.append(gw_thread)

    for node_id in range(NUM_NODES):
        t = threading.Thread(target=iot_node, args=(node_id,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    nodes = list(energy_consumption.keys())
    energy_values = list(energy_consumption.values())
    print("\nTotal Energy Consumption (mJ):")
    for node, energy in energy_consumption.items():
        print(f"Node {node}: {energy:.2f} mJ")
    plt.figure(figsize=(8, 4))
    plt.bar(nodes, energy_values, color="blue")
    plt.xlabel("Node ID")
    plt.ylabel("Energy Consumed (mJ)")
    plt.title("Energy Consumption per Node - Full FHE + HMAC")
    plt.grid(axis="y")
    plt.tight_layout()
    plt.show()




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/archive/codes/main.py =====
import networkx as nx
import simpy
import random
import matplotlib.pyplot as plt
import tenseal as ts

# پارامترهای عمومی
NUM_NODES = 10  # تعداد گره‌های IoT
SIM_TIME = 100  # زمان شبیه‌سازی
ENERGY_PER_BYTE = 0.001  # میلی ژول به ازای هر بایت انتقال داده

# ساختار گراف شبکه
G = nx.erdos_renyi_graph(n=NUM_NODES, p=0.3)
G.add_node("gateway")
for node in range(NUM_NODES):
    G.add_edge(node, "gateway")

# آمار مصرف انرژی و تأخیر
total_energy_consumed = {node: 0.0 for node in range(NUM_NODES)}
total_latency = []

# تنظیم رمزنگاری BFV
context = ts.context(
    ts.SCHEME_TYPE.BFV, poly_modulus_degree=8192, plain_modulus=1032193
)
context.generate_galois_keys()
context.generate_relin_keys()
context.global_scale = 2**40

# تابع تولید داده و ارسال
def iot_node(env, node_id, gateway_pipe):
    while True:
        yield env.timeout(random.randint(5, 15))
        biometric_value = random.randint(1000, 9999)  # داده عددی بیومتریک
        encrypted_data = ts.bfv_vector(context, [biometric_value])
        data_size = len(str(encrypted_data.serialize()))
        energy = data_size * ENERGY_PER_BYTE
        total_energy_consumed[node_id] += energy
        print(
            f"[Time {env.now}] Node {node_id} sends encrypted biometric value to Gateway | Value: {biometric_value} | Energy used: {energy:.3f} mJ"
        )
        yield gateway_pipe.put((env.now, node_id, encrypted_data.serialize()))


# تابع دریافت داده در Gateway
trusted_database = {
    i: i * 1000 + 1234 for i in range(NUM_NODES)
}  # داده بیومتریک مرجع هر کاربر


def gateway(env, gateway_pipe):
    while True:
        timestamp, sender, encrypted_payload = yield gateway_pipe.get()
        latency = env.now - timestamp
        total_latency.append(latency)
        enc_vec = ts.bfv_vector_from(context, encrypted_payload)
        # مقایسه ساده با مقدار مرجع
        ref_val = trusted_database[sender]
        ref_enc = ts.bfv_vector(context, [ref_val])
        diff = enc_vec - ref_enc
        decrypted = diff.decrypt()[0]
        match_status = "MATCH" if decrypted == 0 else "NO MATCH"
        print(
            f"[Time {env.now}] Gateway received from Node {sender} (Latency: {latency}s) → Authentication: {match_status}"
        )


# شبیه‌سازی
env = simpy.Environment()
gateway_pipe = simpy.Store(env)

for node in range(NUM_NODES):
    env.process(iot_node(env, node, gateway_pipe))

env.process(gateway(env, gateway_pipe))

env.run(until=SIM_TIME)

# خروجی نهایی
print("\n--- Simulation Summary ---")
print("Total Energy Consumed (mJ):")
for node, energy in total_energy_consumed.items():
    print(f"Node {node}: {energy:.2f} mJ")

avg_latency = sum(total_latency) / len(total_latency) if total_latency else 0
print(f"\nAverage Latency: {avg_latency:.2f} seconds")

# نمودار مصرف انرژی
nodes = list(total_energy_consumed.keys())
energy_values = list(total_energy_consumed.values())

plt.figure(figsize=(10, 5))
plt.bar(nodes, energy_values, color="skyblue")
plt.xlabel("Node ID")
plt.ylabel("Energy Consumed (mJ)")
plt.title("Energy Consumption per IoT Node")
plt.grid(True)
plt.tight_layout()
plt.show()




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/archive/codes/jwt_simulation_v2.py =====
import time
import jwt
import random
import json
import threading
import paho.mqtt.client as mqtt
import matplotlib.pyplot as plt

NUM_NODES = 10
MSGS_PER_NODE = 15
ENERGY_PER_BYTE = 0.001
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
TOPIC = "iot/biometric/jwt"
JWT_SECRET = "my_jwt_secret_key"

energy_consumption_jwt = {node: 0.0 for node in range(NUM_NODES)}
lock = threading.Lock()
trusted_database = {i: i * 1000 + 1234 for i in range(NUM_NODES)}


def iot_node_jwt(node_id):
    client = mqtt.Client()
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()

    for _ in range(MSGS_PER_NODE):
        time.sleep(random.uniform(0.5, 2))
        biometric_value = random.randint(1000, 9999)
        timestamp = time.time()

        payload = {
            "node_id": node_id,
            "timestamp": timestamp,
            "biometric": biometric_value,
        }

        token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        packet = json.dumps({"jwt": token})
        msg_bytes = packet.encode("utf-8")

        with lock:
            energy_consumption_jwt[node_id] += len(msg_bytes) * ENERGY_PER_BYTE

        print(
            f"[Node {node_id}] Sent JWT | Energy: {len(msg_bytes)*ENERGY_PER_BYTE:.3f} mJ"
        )
        client.publish(TOPIC, packet)

    client.loop_stop()
    client.disconnect()


def gateway_jwt():
    client = mqtt.Client()

    def on_connect(client, userdata, flags, rc):
        client.subscribe(TOPIC)

    def on_message(client, userdata, msg):
        message = json.loads(msg.payload.decode("utf-8"))
        try:
            decoded = jwt.decode(message["jwt"], JWT_SECRET, algorithms=["HS256"])
            node_id = decoded["node_id"]
            biometric = decoded["biometric"]
            ref_val = trusted_database.get(node_id, None)
            match_status = (
                "MATCH" if ref_val and abs(ref_val - biometric) < 100 else "NO MATCH"
            )
            print(
                f"[Gateway-JWT] Node {node_id} Biometric: {biometric} → {match_status}"
            )
        except jwt.exceptions.InvalidTokenError:
            print("[Gateway-JWT] Invalid JWT")

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
    time.sleep((MSGS_PER_NODE + 5) * NUM_NODES)
    client.loop_stop()
    client.disconnect()


if __name__ == "__main__":
    threads = []

    gw_thread = threading.Thread(target=gateway_jwt)
    gw_thread.start()
    threads.append(gw_thread)

    for node_id in range(NUM_NODES):
        t = threading.Thread(target=iot_node_jwt, args=(node_id,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    print("\nTotal Energy Consumption (mJ) - JWT:")
    for node, energy in energy_consumption_jwt.items():
        print(f"Node {node}: {energy:.2f} mJ")

    nodes = list(energy_consumption_jwt.keys())
    energy_values = list(energy_consumption_jwt.values())
    plt.figure(figsize=(8, 4))
    plt.bar(nodes, energy_values, color="orange")
    plt.xlabel("Node ID")
    plt.ylabel("Energy Consumed (mJ)")
    plt.title("Energy Consumption per Node - JWT Authentication")
    plt.grid(axis="y")
    plt.tight_layout()
    plt.show()




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/archive/codes/simulation_no_encryption.py =====
import networkx as nx
import simpy
import random
import matplotlib.pyplot as plt

# پارامترهای عمومی
NUM_NODES = 10  # تعداد گره‌های IoT
SIM_TIME = 100  # زمان شبیه‌سازی
ENERGY_PER_BYTE = 0.001  # میلی ژول به ازای هر بایت انتقال داده

# ساختار گراف شبکه
G = nx.erdos_renyi_graph(n=NUM_NODES, p=0.3)
G.add_node("gateway")
for node in range(NUM_NODES):
    G.add_edge(node, "gateway")

# آمار مصرف انرژی و تأخیر
total_energy_consumed = {node: 0.0 for node in range(NUM_NODES)}
total_latency = []

# تابع تولید داده و ارسال
def iot_node(env, node_id, gateway_pipe):
    while True:
        yield env.timeout(random.randint(5, 15))
        biometric_value = random.randint(1000, 9999)  # داده عددی بیومتریک
        data_size = len(str(biometric_value).encode("utf-8"))
        energy = data_size * ENERGY_PER_BYTE
        total_energy_consumed[node_id] += energy
        print(
            f"[Time {env.now}] Node {node_id} sends biometric value to Gateway | Value: {biometric_value} | Energy used: {energy:.3f} mJ"
        )
        yield gateway_pipe.put((env.now, node_id, biometric_value))


# تابع دریافت داده در Gateway
trusted_database = {
    i: i * 1000 + 1234 for i in range(NUM_NODES)
}  # داده بیومتریک مرجع هر کاربر


def gateway(env, gateway_pipe):
    while True:
        timestamp, sender, payload = yield gateway_pipe.get()
        latency = env.now - timestamp
        total_latency.append(latency)
        ref_val = trusted_database[sender]
        match_status = "MATCH" if payload == ref_val else "NO MATCH"
        print(
            f"[Time {env.now}] Gateway received from Node {sender} (Latency: {latency}s) → Authentication: {match_status}"
        )


# شبیه‌سازی
env = simpy.Environment()
gateway_pipe = simpy.Store(env)

for node in range(NUM_NODES):
    env.process(iot_node(env, node, gateway_pipe))

env.process(gateway(env, gateway_pipe))

env.run(until=SIM_TIME)

# خروجی نهایی
print("\n--- Simulation Summary ---")
print("Total Energy Consumed (mJ):")
for node, energy in total_energy_consumed.items():
    print(f"Node {node}: {energy:.2f} mJ")

avg_latency = sum(total_latency) / len(total_latency) if total_latency else 0
print(f"\nAverage Latency: {avg_latency:.2f} seconds")

# نمودار مصرف انرژی
nodes = list(total_energy_consumed.keys())
energy_values = list(total_energy_consumed.values())

plt.figure(figsize=(10, 5))
plt.bar(nodes, energy_values, color="salmon")
plt.xlabel("Node ID")
plt.ylabel("Energy Consumed (mJ)")
plt.title("Energy Consumption per IoT Node (No Encryption)")
plt.grid(True)
plt.tight_layout()
plt.savefig("./energy_no_encryption.png")




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/archive/codes/Hybrid_2_with_new_changes_with_data_compression.py =====
import time
import hmac
import hashlib
import tenseal as ts
import paho.mqtt.client as mqtt
import json
import threading
import base64
import random
import matplotlib.pyplot as plt
from collections import defaultdict, deque
import gzip

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

context = ts.context(
    ts.SCHEME_TYPE.BFV, poly_modulus_degree=POLY_MOD_DEGREE, plain_modulus=1032193
)
context.generate_galois_keys()
context.generate_relin_keys()
context.global_scale = 2**40

energy_consumption = {node: 0.0 for node in range(NUM_NODES)}
recent_timestamps = defaultdict(lambda: deque(maxlen=100))
with open(OUTPUT_FILE, "w", newline="") as f:
    f.write("node_id,latency_ms,bytes,battery\n")

lock = threading.Lock()
trusted_database = {i: i * 1000 + 1234 for i in range(NUM_NODES)}


def generate_hmac(message: str) -> str:
    return hmac.new(SHARED_SECRET, message.encode(), hashlib.sha256).hexdigest()


def iot_node(node_id):
    client = mqtt.Client()
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()

    battery_level = BATTERY_DEFAULT_VALUE
    batch_plain = []

    for msg_count in range(1, MSGS_PER_NODE + 1):
        time.sleep(random.uniform(0.5, 2))
        biometric_value = random.randint(1000, 9999)
        timestamp = time.time()
        message_light = f"{node_id}:{timestamp}:{biometric_value}"
        signature = generate_hmac(message_light)

        battery_level -= random.randint(1, 2)

        payload = None
        msg_bytes = None
        encoded_compressed = None

        if msg_count % FHE_INTERVAL == 0:
            batch_plain.append(
                {
                    "biometric": biometric_value,
                    "timestamp": timestamp,
                    "hmac": signature,
                }
            )
            enc_batch = [entry["biometric"] for entry in batch_plain]
            enc_vec = ts.bfv_vector(context, enc_batch)
            serialized_enc = base64.b64encode(enc_vec.serialize()).decode("utf-8")

            payload = {
                "node_id": node_id,
                "battery_level": battery_level,
                "batch_HMAC": [entry["hmac"] for entry in batch_plain],
                "batch_timestamps": [entry["timestamp"] for entry in batch_plain],
                "enc_biometrics": serialized_enc,
                "batch_size": len(batch_plain),
            }
            payload_str = json.dumps(payload)
            compressed = gzip.compress(payload_str.encode("utf-8"))
            encoded_compressed = base64.b64encode(compressed).decode("utf-8")
            # msg_bytes = payload_str.encode('utf-8')
            msg_bytes = encoded_compressed.encode("utf-8")
            print(
                f"[Node {node_id}] Sent BATCH with FHE ({len(batch_plain)} recs) | Energy: {len(msg_bytes)*ENERGY_PER_BYTE:.3f} mJ | Battery: {battery_level}"
            )
            batch_plain = []

        else:
            if battery_level < BATTERY_THRESHOLD:
                payload = {
                    "node_id": node_id,
                    "type": "light",
                    "battery_level": battery_level,
                    "hmac": signature,
                    "timestamp": timestamp,
                    "biometric": biometric_value,
                }
                payload_str = json.dumps(payload)
                compressed = gzip.compress(payload_str.encode("utf-8"))
                encoded_compressed = base64.b64encode(compressed).decode("utf-8")
                # msg_bytes = payload_str.encode('utf-8')
                msg_bytes = encoded_compressed.encode("utf-8")
                print(
                    f"[Node {node_id}] Sent ONLY HMAC (Battery Low) | Energy: {len(msg_bytes)*ENERGY_PER_BYTE:.3f} mJ | Battery: {battery_level}"
                )
            else:
                batch_plain.append(
                    {
                        "biometric": biometric_value,
                        "timestamp": timestamp,
                        "hmac": signature,
                    }
                )
                continue

        with lock:
            energy_consumption[node_id] += len(msg_bytes) * ENERGY_PER_BYTE

        send_time_ns = time.time_ns()
        payload["send_time_ns"] = send_time_ns
        payload_str = json.dumps(payload)
        msg_bytes = payload_str.encode("utf-8")
        # qos=1 ensures message delivery
        # client.publish(TOPIC, payload_str, qos=1)
        client.publish(TOPIC, encoded_compressed, qos=1)

    client.loop_stop()
    client.disconnect()


def gateway():
    client = mqtt.Client()

    def on_connect(client, userdata, flags, rc):
        client.subscribe(TOPIC)

    def on_message(client, userdata, msg):
        compressed_payload = base64.b64decode(msg.payload)
        decompressed_json = gzip.decompress(compressed_payload).decode("utf-8")
        payload = json.loads(decompressed_json)
        # payload = json.loads(msg.payload.decode('utf-8'))
        receive_time_ns = time.time_ns()
        node_id = payload["node_id"]

        if "enc_biometrics" in payload:
            base_latency = receive_time_ns - payload["batch_timestamps"][0] * 1e9
            latency_ms = base_latency / 1_000_000
        else:
            latency_ms = (receive_time_ns - payload["send_time_ns"]) / 1_000_000

        try:
            with open(OUTPUT_FILE, "a", newline="") as f:
                f.write(
                    f"{node_id},{latency_ms:.2f},{len(msg.payload)},{payload.get('battery_level',-1)}\n"
                )
        except Exception as e:
            print(f"[Gateway] Write CSV ERROR: {e}")

        # if not is_fresh(node_id, timestamp):
        #     print(f"[Gateway] Replay detected from Node {node_id}")
        #     return

        if "enc_biometrics" in payload:
            enc_bytes = base64.b64decode(payload["enc_biometrics"])
            dec_start = time.time()
            vec = ts.bfv_vector_from(context, enc_bytes)
            decrypted_values = vec.decrypt()
            dec_time = time.time() - dec_start
            print(
                f"[Gateway] Received BATCH from Node {node_id} | Decryption Time: {dec_time:.4f} sec"
            )

            for i, val in enumerate(decrypted_values):
                timestamp = payload["batch_timestamps"][i]
                hmac_expected = generate_hmac(f"{node_id}:{timestamp}:{val}")
                valid = hmac.compare_digest(payload["batch_HMAC"][i], hmac_expected)
                ref_val = trusted_database.get(node_id, None)
                match_status = (
                    "MATCH" if ref_val and abs(ref_val - val) < 100 else "NO MATCH"
                )
                print(f"→ Biometric: {val} | HMAC: {valid} | Match: {match_status}")

        elif payload.get("type") == "light":
            biometric = payload["biometric"]
            timestamp = payload["timestamp"]
            hmac_expected = generate_hmac(f"{node_id}:{timestamp}:{biometric}")
            valid = hmac.compare_digest(payload["hmac"], hmac_expected)
            ref_val = trusted_database.get(node_id, None)
            match_status = (
                "MATCH" if ref_val and abs(ref_val - biometric) < 100 else "NO MATCH"
            )
            print(
                f"[Gateway] Light AUTH from Node {node_id} | HMAC: {valid} | Match: {match_status}"
            )

    def is_fresh(node_id, ts):
        dq = recent_timestamps[node_id]
        now = time.time()
        while dq and now - dq[0] > REPLAY_WINDOW_SEC:
            dq.popleft()
        if ts in dq:
            return False
        dq.append(ts)
        return True

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
    time.sleep((MSGS_PER_NODE + 5) * NUM_NODES)
    client.loop_stop()
    client.disconnect()


if __name__ == "__main__":
    threads = []

    gw_thread = threading.Thread(target=gateway)
    gw_thread.start()
    threads.append(gw_thread)

    for node_id in range(NUM_NODES):
        t = threading.Thread(target=iot_node, args=(node_id,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    nodes = list(energy_consumption.keys())
    energy_values = list(energy_consumption.values())
    print("\nTotal Energy Consumption (mJ):")
    for node, energy in energy_consumption.items():
        print(f"Node {node}: {energy:.2f} mJ")
    plt.figure(figsize=(8, 4))
    plt.bar(nodes, energy_values, color="purple")
    plt.xlabel("Node ID")
    plt.ylabel("Energy Consumed (mJ)")
    plt.title("Energy Consumption per Node - Adaptive Batching & Crypto")
    plt.grid(axis="y")
    plt.tight_layout()
    plt.show()




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/output/__init__.py =====




# ===== File: /Users/thesam/Desktop/project/PythonProjects/srb/thesis/main/output/logs/__init__.py =====



