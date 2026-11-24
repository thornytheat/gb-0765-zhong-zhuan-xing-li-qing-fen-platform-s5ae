from flask import Blueprint, current_app, jsonify, request, url_for

from app.errors import DeskError
from app.modules.archive.routes import store
from .bundle import certify
from .service import index
from .station import certify_station, destinations, summary
from .tickets import Tickets

bp = Blueprint('evidence', __name__)


def tickets():
    return current_app.extensions['evidence_tickets']


def run_bundle(run):
    files, result = store().get(run)
    return files, result


@bp.get('/api/evidence/<run>')
def evidence(run):
    return jsonify(index(*store().get(run)))


@bp.get('/api/evidence/<run>/export')
def export(run):
    files, result = store().get(run)
    station_name = request.args.get('station')
    if station_name:
        return _station_download(run, files, result, station_name,
                                 f'transfer-{run}-{station_name}.json')
    response = jsonify(certify(files, result))
    response.headers['Content-Disposition'] = f'attachment; filename="transfer-{run}.json"'
    return response


@bp.get('/api/evidence/<run>/stations/<destination>/export')
@bp.get('/api/evidence/<run>/station/<destination>/export')
def station_export(run, destination):
    files, result = store().get(run)
    return _station_download(run, files, result, destination,
                             f'transfer-{run}-{destination}.json')


def _station_download(run, files, result, destination, filename):
    bundle = certify_station(files, result, destination)
    issued = [ticket for ticket in tickets().list(run) if ticket['destination'] == destination]
    # A withdrawn receipt permission covers every download surface for that
    # station, not only the ticket URL that was handed out first.
    if issued and not any(ticket['usable'] for ticket in issued):
        raise DeskError('TICKET_REVOKED', '收件权限已撤回', 403)
    response = jsonify(bundle)
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@bp.get('/api/evidence/<run>/stations')
def stations(run):
    files, result = store().get(run)
    certify(files, result)
    return jsonify(run=run, rows=[summary(files, result, destination)
                                  for destination in destinations(result['stages'])])

@bp.get('/api/evidence/<run>/stations/<destination>')
@bp.get('/api/evidence/<run>/station/<destination>')
def station(run, destination):
    files, result = store().get(run)
    return jsonify(certify_station(files, result, destination))


@bp.post('/api/evidence/<run>/stations/<destination>')
@bp.post('/api/evidence/<run>/station/<destination>')
@bp.post('/api/evidence/<run>/stations/<destination>/issue')
def issue(run, destination):
    files, result = store().get(run)
    bundle = certify_station(files, result, destination)
    ticket = tickets().issue(run, destination, bundle['bundle_sha256'])
    return jsonify(_with_link(ticket, bundle))


@bp.post('/api/evidence/<run>/stations/<destination>/revoke')
@bp.post('/api/evidence/<run>/station/<destination>/revoke')
def revoke_station(run, destination):
    files, result = store().get(run)
    bundle = certify_station(files, result, destination)
    return jsonify(run=run, destination=destination, payload_sha256=bundle['bundle_sha256'],
                   revoked=tickets().revoke_where(run, destination))


@bp.get('/api/evidence/tickets')
def ticket_list():
    run = request.args.get('run')
    return jsonify(rows=[_with_link(ticket) for ticket in tickets().list(run)])


@bp.get('/api/evidence/ticket/<ticket>')
def ticket_detail(ticket):
    return jsonify(_with_link(tickets().resolve(ticket)))


@bp.post('/api/evidence/ticket/<ticket>/revoke')
def revoke_ticket(ticket):
    return jsonify(_with_link(tickets().revoke(ticket)))


@bp.get('/api/evidence/ticket/<ticket>/export')
def download(ticket):
    record = tickets().resolve(ticket)
    if not record['usable']:
        raise DeskError('TICKET_REVOKED', '收件权限已撤回', 403)
    files, result = run_bundle(record['run'])
    bundle = certify_station(files, result, record['destination'])
    if bundle['bundle_sha256'] != record['payload_sha256']:
        raise DeskError('UNVERIFIED', '证据内容与签发摘要不符', 409)
    response = jsonify(bundle)
    response.headers['Content-Disposition'] = (
        f'attachment; filename="transfer-{record["run"]}-{record["token"][:8]}.json"')
    return response


def _with_link(record, bundle=None):
    view = dict(record)
    view['download_url'] = url_for('evidence.download', ticket=record['token']) if record['usable'] else None
    if bundle is not None:
        view['counts'] = bundle['counts']
        view['reconciliation'] = bundle['reconciliation']
        view['bundle_sha256'] = bundle['bundle_sha256']
    return view
