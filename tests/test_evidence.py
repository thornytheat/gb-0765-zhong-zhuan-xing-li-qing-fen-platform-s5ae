import pytest
from app.errors import DeskError
from app.input import sample
from app.modules.evidence.bundle import certify


def test_attachment(desk, saved):
    response = desk.get(f"/api/evidence/{saved['id']}/export")
    assert 'attachment;' in response.headers['Content-Disposition']
    assert response.json['originals']['scans.csv'].startswith('\ufeff')


def test_source_hash(desk, saved):
    payload = desk.get(f"/api/evidence/{saved['id']}").json
    assert {row['source']: row['sha256'] for row in payload['rows']} == saved['manifest']['inputs']


def test_tampered_original(desk, saved):
    store = desk.application.extensions['transfer_archive']
    files, result = store.get(saved['id'])
    files['legs.csv'] += '\n'
    with pytest.raises(DeskError, match='摘要'):
        certify(files, result)


def test_tampered_stage(desk, saved):
    _, result = desk.application.extensions['transfer_archive'].get(saved['id'])
    result['stages']['ledger']['counts']['loaded'] = 99
    with pytest.raises(DeskError, match='摘要'):
        certify(sample('dirty'), result)


def test_missing_export(desk):
    assert desk.get('/api/evidence/unknown/export').status_code == 404


def test_conflicting_originals_in_bundle(desk, saved):
    payload = desk.get(f"/api/evidence/{saved['id']}/export").json
    assert payload['stages']['scans']['reasons']['ID_CONFLICT'] == 2
