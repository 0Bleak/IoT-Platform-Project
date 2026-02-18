import hmac, hashlib, json, time, secrets

def load_key(path="secrets/device1.key") -> bytes:
    with open(path, "rb") as f:
        return f.read().strip()

def canonical_json(obj: dict) -> str:
    return json.dumps(obj, separators=(",", ":"), sort_keys=True)

def sign_payload(key: bytes, payload_wo_hmac: dict) -> str:
    msg = canonical_json(payload_wo_hmac).encode("utf-8")
    tag = hmac.new(key, msg, hashlib.sha256).hexdigest()
    return tag

def make_metrics_message(device_id: str, data: dict, key: bytes) -> dict:
    payload = {
        "device_id": device_id,
        "ts_ms": int(time.time() * 1000),
        "nonce": secrets.token_hex(4),
        "data": data
    }
    payload["hmac"] = sign_payload(key, payload)
    return payload
