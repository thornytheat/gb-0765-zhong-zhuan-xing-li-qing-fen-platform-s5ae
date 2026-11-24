from datetime import datetime, timezone


def utc(value):
    stamp = datetime.fromisoformat(value)
    if stamp.utcoffset() is None:
        raise ValueError('timezone required')
    return stamp.astimezone(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')
