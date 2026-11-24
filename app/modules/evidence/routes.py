from flask import Blueprint, jsonify
from app.modules.archive.routes import store
from .bundle import certify
from .service import index

bp = Blueprint('evidence', __name__)


@bp.get('/api/evidence/<run>')
def evidence(run):
    return jsonify(index(*store().get(run)))


@bp.get('/api/evidence/<run>/export')
def export(run):
    response = jsonify(certify(*store().get(run)))
    response.headers['Content-Disposition'] = f'attachment; filename="transfer-{run}.json"'
    return response
