import hmac
import hashlib

from settings import SHARED_SECRET


def node_key(node_id) -> bytes:
    """Per-node 256-bit HMAC key K_mac,i, derived from the provisioning secret (stands in for enrollment-time provisioning)."""
    return hmac.new(SHARED_SECRET, f"K_mac:{node_id}".encode(), hashlib.sha256).digest()


def generate_hmac(message: str, node_id) -> str:
    return hmac.new(node_key(node_id), message.encode(), hashlib.sha256).hexdigest()


def hmac_message(node_id, timestamp, vector) -> str:
    """Canonical string tagged for one reading: node_id : timestamp : comma-separated quantized features."""
    return f"{node_id}:{timestamp}:{','.join(str(int(v)) for v in vector)}"
