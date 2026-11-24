from datetime import datetime, timezone
from hashlib import sha256
from time import perf_counter_ns

from app.config import VERSION
from app.errors import DeskError
from app.manifest import fingerprint


def archive(store, files, compute):
    started = perf_counter_ns()
    hashes = {name: sha256(text.encode()).hexdigest() for name, text in files.items()}
    key = fingerprint([VERSION, hashes])
    stages = compute(files)
    manifest = dict(id=key, version=VERSION, inputs=hashes, result_sha256=fingerprint(stages),
                    generated_at=datetime.now(timezone.utc).isoformat(), elapsed_us=(perf_counter_ns() - started) // 1000)
    result, reused = store.commit(key, files, dict(manifest=manifest, stages=stages))
    if (result['manifest']['result_sha256'] != manifest['result_sha256'] or
            fingerprint(result['stages']) != manifest['result_sha256']):
        raise DeskError('REPLAY_DRIFT', '复算结果与归档摘要不符', 409)
    return dict(id=key, reused=reused, manifest=result['manifest'], counts=result['stages']['ledger']['counts'])
