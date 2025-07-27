import base64
import json
import gzip


def compress_data(payload: dict) -> str:
    payload_str = json.dumps(payload)
    compressed = gzip.compress(payload_str.encode("utf-8"))
    return base64.b64encode(compressed).decode("utf-8")
