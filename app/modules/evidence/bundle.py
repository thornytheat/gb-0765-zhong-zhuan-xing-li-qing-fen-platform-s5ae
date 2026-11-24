from hashlib import sha256

from app.errors import DeskError
from app.manifest import fingerprint
from app.reasons import REASONS


def certify(files, result):
    manifest, stages = result['manifest'], result['stages']
    actual = {name: sha256(text.encode()).hexdigest() for name, text in files.items()}
    if actual != manifest['inputs'] or fingerprint(stages) != manifest['result_sha256'] or not stages['ledger']['balanced']:
        raise DeskError('UNVERIFIED', '证据摘要或件数勾稽不符', 409)
    return dict(manifest=manifest, originals=files, stages=stages, reasons=REASONS, verified=True)
