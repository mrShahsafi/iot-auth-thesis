import base64
import gzip
import hmac
import json
import math
import time

import paho.mqtt.client as mqtt
import tenseal as ts

from settings import (
    TOPIC,
    REPLAY_WINDOW_SEC,
    MQTT_PORT,
    MQTT_BROKER,
    MSGS_PER_NODE,
    NUM_NODES,
    LOG_CSV,
    MODE,
    FHE_INTERVAL,
    FEATURE_DIM,
    MATCH_THRESHOLD,
    ENERGY_PER_BYTE,
)
from ..core import ACK_TOPIC, DECISION_TOPIC, generate_hmac, hmac_message, signed, verify
from ..utils.metrics import CSV_FIELDS


def gateway(context, trusted_database, recent_timestamps, dry_run=False):
    """Trusted gateway: freshness check, decrypt the packed batch, verify each reading's HMAC,
    squared distance to the enrolled template, threshold, then publish the signed decision (message 2) and log the
    row when the node's signed acknowledgement (message 3) arrives."""
    client = mqtt.Client()
    received = 0
    per_node = MSGS_PER_NODE if MODE == "Plain" else math.ceil(MSGS_PER_NODE / FHE_INTERVAL)
    expected = NUM_NODES * per_node
    pending = {}  # (node_id, t_capture_first) -> log row waiting for the ack

    def log(**row):
        if dry_run:
            return
        with open(LOG_CSV, "a", newline="") as f:
            f.write(",".join(f"{row.get(c, 0):.3f}" if isinstance(row.get(c, 0), float) else str(row.get(c, 0)) for c in CSV_FIELDS) + "\n")

    def is_fresh(node_id, ts):
        dq, now, window = recent_timestamps[node_id], time.time(), float(REPLAY_WINDOW_SEC)
        ts = float(ts)
        while dq and now - dq[0] > window:
            dq.popleft()
        if now - ts > window or ts in dq:
            return False
        dq.append(ts)
        return True

    def on_message(client, userdata, msg):
        nonlocal received
        t_recv = time.time()
        raw = gzip.decompress(base64.b64decode(msg.payload)) if MODE == "Hybrid" else msg.payload
        payload = json.loads(raw.decode("utf-8"))
        node_id, k, stamps = payload["node_id"], payload["batch_size"], payload["batch_timestamps"]
        base = dict(node_id=node_id, k=k, bytes=len(msg.payload), battery=payload.get("battery_level", -1),
                    energy=len(msg.payload) * ENERGY_PER_BYTE)
        if not all(is_fresh(node_id, t) for t in stamps):
            print(f"[Gateway] Replay detected from Node {node_id}")
            log(**base, replay=1)
            return
        received += 1
        if payload.get("type") == "light":
            log(**base, light=1)
            print(f"[Gateway] Light ping from Node {node_id} ({k} tags)")
            return
        t0 = time.time()
        values = ts.bfv_vector_from(context, base64.b64decode(payload["enc_biometrics"])).decrypt()
        t_dec = time.time()
        template = trusted_database[node_id]["template"]
        genuine = impostor = gen_acc = imp_acc = hmac_failed = 0
        decisions = []
        for i in range(k):
            vec = values[i * FEATURE_DIM:(i + 1) * FEATURE_DIM]
            tag_ok = hmac.compare_digest(payload["batch_HMAC"][i], generate_hmac(hmac_message(node_id, stamps[i], vec), node_id))
            dist = sum((a - b) ** 2 for a, b in zip(vec, template))
            accepted = tag_ok and dist <= MATCH_THRESHOLD
            hmac_failed += not tag_ok
            decisions.append(int(accepted))
            if payload["labels"][i]:
                genuine += 1; gen_acc += accepted
            else:
                impostor += 1; imp_acc += accepted
        t_match = time.time()
        row = dict(**base,
            latency_ms=(t_recv - payload["t_capture_first"]) * 1e3,
            wait_ms=(payload["t_capture_last"] - payload["t_capture_first"]) * 1e3,
            enc_ms=(payload["t_enc_end"] - payload["t_enc_start"]) * 1e3,
            transport_ms=(t_recv - payload["t_publish"]) * 1e3,
            dec_ms=(t_dec - t0) * 1e3, match_ms=(t_match - t_dec) * 1e3,
            genuine=genuine, impostor=impostor, genuine_accepted=gen_acc, impostor_accepted=imp_acc,
            hmac_failed=hmac_failed)
        decision = signed(node_id, {"t_capture_first": payload["t_capture_first"], "decisions": decisions})
        row["decision_bytes"] = len(decision)
        pending[(node_id, payload["t_capture_first"])] = row
        client.publish(DECISION_TOPIC.format(node_id), decision, qos=1)
        print(f"[Gateway] Node {node_id} batch k={k}: genuine {gen_acc}/{genuine} accepted, "
              f"impostor {imp_acc}/{impostor} accepted, HMAC failures {hmac_failed}, decrypt {(t_dec - t0) * 1e3:.1f} ms")

    def on_ack(client, userdata, msg):
        ok, node_id, body = verify(msg.payload)
        row = pending.pop((node_id, body["t_capture_first"]), None) if ok else None
        if row is None:
            return
        row.update(decision_ms=(body["t_decision_recv"] - body["t_capture_first"]) * 1e3, ack_bytes=len(msg.payload))
        row["energy"] += len(msg.payload) * ENERGY_PER_BYTE  # node transmit energy: request + ack
        log(**row)

    client.on_connect = lambda c, u, f, rc: c.subscribe([(TOPIC, 0), (ACK_TOPIC, 1)])
    client.on_message = on_message
    client.message_callback_add(ACK_TOPIC, on_ack)
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
    start = time.time()
    while (received < expected or pending) and time.time() - start < 180:
        time.sleep(0.5)
    time.sleep(3)  # stragglers and replayed copies
    for row in pending.values():  # decided but never acknowledged
        log(**row, decision_ms=-1.0)
    client.loop_stop()
    client.disconnect()
    print(f"[Gateway] {received}/{expected} messages received")
