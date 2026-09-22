import hashlib
import hmac
import time
import uuid

from core.config import settings


def create_service_headers(
    method,
    path,
    body,
):

    timestamp = int(time.time())
    nonce = str(uuid.uuid4())

    message = (
        f"{method}\n"
        f"{path}\n"
        f"{timestamp}\n"
        f"{nonce}\n"
        f"{body}"
    )

    signature = hmac.new(
        settings.SERVICE_SECRET.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()

    return {
        "X-Service-ID": settings.SERVICE_ID,
        "X-Timestamp": str(timestamp),
        "X-Nonce": nonce,
        "X-Signature": signature,
    }