from .bundle import certify


def index(files, result):
    bundle = certify(files, result)
    return dict(verified=True, manifest=bundle['manifest'],
                rows=[dict(source=name, sha256=bundle['manifest']['inputs'][name]) for name in sorted(files)])
