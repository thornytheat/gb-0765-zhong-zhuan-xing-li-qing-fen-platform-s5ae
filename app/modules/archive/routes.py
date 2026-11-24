from flask import Blueprint, current_app, jsonify, request
from app.input import submission
from app.pipeline import compute
from .service import archive

bp = Blueprint('archive', __name__)


def store():
    return current_app.extensions['transfer_archive']


@bp.get('/api/archive')
def history():
    runs = store().list()
    return jsonify(count=len(runs), rows=runs)


@bp.post('/api/archive')
def save():
    files = submission(request.get_json(silent=True))
    return jsonify(archive(store(), files, compute))


@bp.post('/api/archive/<run>/rerun')
def rerun(run):
    files, _ = store().get(run)
    return jsonify(archive(store(), files, compute))


@bp.get('/api/archive/<run>')
def detail(run):
    _, result = store().get(run)
    return jsonify(id=run, manifest=result['manifest'], counts=result['stages']['ledger']['counts'])
