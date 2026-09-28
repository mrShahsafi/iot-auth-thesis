"""Messages 2 and 3 of the protocol: the gateway's signed decision and the node's signed acknowledgement."""
import hmac
import json
import time

from settings import ENERGY_PER_BYTE, TOPIC

from .encryption import generate_hmac

DECISION_TOPIC = TOPIC + "/decision/{}"
ACK_TOPIC = TOPIC + "/ack"


def _tagged(node_id, ts, body):
    return f"{node_id}:{ts}:{json.dumps(body, sort_keys=True)}"


def signed(node_id, body):
    """JSON message carrying body, a timestamp and the HMAC of node_id's key over both."""
    ts = round(time.time(), 3)
    return json.dumps({"node_id": node_id, "ts": ts, **body, "hmac": generate_hmac(_tagged(node_id, ts, body), node_id)})


def verify(raw):
    """-> (tag valid, node_id, body)."""
    m = json.loads(raw)
    tag, node_id, ts = m.pop("hmac"), m.pop("node_id"), m.pop("ts")
    return hmac.compare_digest(tag, generate_hmac(_tagged(node_id, ts, m), node_id)), node_id, m


def ack_decisions(client, node_id, lock, energy_consumption, outstanding):
    """Node side: answer each authentic decision for one of this node's outstanding batches with a signed ack.
    outstanding holds the t_capture_first of every batch sent and not yet decided (it doubles as the nonce)."""
    def on_decision(c, userdata, msg):
        t_recv = time.time()
        ok, nid, body = verify(msg.payload)
        if not ok or nid != node_id or body["t_capture_first"] not in outstanding:
            return
        outstanding.discard(body["t_capture_first"])
        ack = signed(node_id, {"t_capture_first": body["t_capture_first"], "t_decision_recv": t_recv})
        with lock:
            energy_consumption[node_id] += len(ack) * ENERGY_PER_BYTE
        c.publish(ACK_TOPIC, ack, qos=1)

    topic = DECISION_TOPIC.format(node_id)
    client.message_callback_add(topic, on_decision)
    client.subscribe(topic, qos=1)


def wait_for_decisions(outstanding, timeout=15):
    deadline = time.time() + timeout
    while outstanding and time.time() < deadline:
        time.sleep(0.1)
