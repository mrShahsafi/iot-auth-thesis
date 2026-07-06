import hmac
import hashlib

from settings import SHARED_SECRET


def generate_hmac(message: str) -> str:
    return hmac.new(SHARED_SECRET, message.encode(), hashlib.sha256).hexdigest()
