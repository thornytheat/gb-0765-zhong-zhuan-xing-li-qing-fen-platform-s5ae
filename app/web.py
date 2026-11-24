from flask import Blueprint, jsonify, render_template, request
from .errors import DeskError
from .input import sample, submission
from .modules.archive.routes import store
from .modules.evidence.service import index
from .pipeline import compute
from .reasons import REASONS

DESK = {
    'scans': '扫描原件', 'legs': '航段候选', 'replay': '扫件回放', 'exceptions': '错载与漏扫',
    'ledger': '去向对账', 'archive': '批次留档', 'evidence': '联程证据',
}
bp = Blueprint('desk', __name__)


def snapshot():
    run = request.args.get('run')
    name = request.args.get('sample', 'dirty')
    if run:
        files, result = store().get(run)
        return files, result['stages'], result['manifest'], name
    files = sample(name)
    return files, compute(files), None, name


@bp.get('/api/stage/<key>')
def stage_api(key):
    if key not in tuple(DESK)[:5]:
        raise DeskError('NO_STAGE', '业务入口不存在', 404)
    run = request.args.get('run')
    if run:
        return jsonify(store().get(run)[1]['stages'][key])
    return jsonify(compute(sample(request.args.get('sample', 'dirty')), until=key))


@bp.post('/api/stage/<key>')
def inspect_stage(key):
    if key not in tuple(DESK)[:5]:
        raise DeskError('NO_STAGE', '业务入口不存在', 404)
    return jsonify(compute(submission(request.get_json(silent=True)), until=key))


@bp.get('/', defaults={'key': 'ledger'})
@bp.get('/desk/<key>')
def desk(key):
    if key not in DESK:
        raise DeskError('NO_STAGE', '业务入口不存在', 404)
    files, stages, manifest, name = snapshot()
    context = dict(stages=stages, ledger=stages['ledger']['counts'], names=DESK, key=key, reasons=REASONS,
                   selected=name, manifest=manifest, archive=store().list() if key == 'archive' else [],
                   report=index(files, dict(stages=stages, manifest=manifest)) if key == 'evidence' and manifest else None)
    return render_template('desk.html', **context)
