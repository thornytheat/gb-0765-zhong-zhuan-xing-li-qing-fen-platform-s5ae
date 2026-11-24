from hashlib import sha256
import json


def canonical(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def fingerprint(data):
    return sha256(canonical(data).encode()).hexdigest()
