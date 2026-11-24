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


def station(client, run, name):
    response = client.get(f'/api/evidence/{run}/stations/{name}')
    assert response.status_code == 200
    return response.json


def test_station_counts_match_ledger_plan(desk, saved):
    payload = desk.get(f"/api/evidence/{saved['id']}/stations").json
    assert {row['destination'] for row in payload['rows']} == {'厦门', '宁波', '福州', '青岛'}
    for row in payload['rows']:
        assert row['counts']['manifest'] == row['counts']['planned'] == row['ledger']['manifest']
        assert row['counts']['manifest'] == row['reconciliation']['ledger_manifest']
        assert {field: row['counts'][field] for field in
                ('manifest', 'loaded', 'pending', 'not_loaded', 'wrong_bags', 'wrong_legs')} == {
                    field: row['ledger'][field] for field in
                    ('manifest', 'loaded', 'pending', 'not_loaded', 'wrong_bags', 'wrong_legs')}
        assert row['reconciliation']['balanced']


def test_station_does_not_leak_other_station_rows(desk, saved):
    bundle = station(desk, saved['id'], '青岛')
    assert bundle['slices']['scans']['lines'] == [12, 13, 17, 23]
    stub, = bundle['redactions']
    assert (stub['line'], stub['reason']) == (18, 'OTHER_STATION')
    assert all(row['line'] != 18 for row in bundle['rows'])


def test_wrong_load_original_at_arrival_station(desk, saved):
    arrival = station(desk, saved['id'], '宁波')
    loaded = next(row for row in arrival['wrong_loads'] if row['tag'] == '000108')
    assert loaded['leg'] == 'NX-02'
    assert loaded['evidence'] == [dict(line=18, source='scans.csv', kind='included')]
    assert [row['line'] for row in arrival['rows']].count(18) == 1


def test_planned_station_only_follows_own_destination(desk, saved):
    planned = station(desk, saved['id'], '青岛')
    bag = next(row for row in planned['dispositions'] if row['tag'] == '000108')
    assert bag['status'] == 'pending' and bag['wrong_legs'] == []
    assert [item['kind'] for item in bag['evidence']] == ['included', 'redacted']
    assert planned['wrong_loads'] == []


def test_ambiguous_leg_withheld_until_resolved(desk, saved):
    for name in ('厦门', '福州'):
        bundle = station(desk, saved['id'], name)
        withheld = {row['line']: row for row in bundle['withheld']}
        assert withheld[8]['reason'] == 'LEG_AMBIGUOUS'
        assert 8 not in bundle['slices']['scans']['lines']
        assert all(row['line'] != 8 for row in bundle['rows'])
        assert station(desk, saved['id'], name)['counts']['manifest'] == 2
        assert station(desk, saved['id'], name)['withholding']['withheld'] == len(bundle['withheld'])


def test_confirmed_evidence_still_downloads(desk, saved):
    ticket = desk.post(f"/api/evidence/{saved['id']}/stations/厦门").json
    response = desk.get(ticket['download_url'])
    assert response.status_code == 200 and response.json['destination'] == '厦门'


def test_issue_is_idempotent(desk, saved):
    first = desk.post(f"/api/evidence/{saved['id']}/stations/宁波").json
    again = desk.post(f"/api/evidence/{saved['id']}/stations/宁波").json
    assert (first['id'], first['download_url']) == (again['id'], again['download_url'])
    assert len(desk.get(f"/api/evidence/tickets?run={saved['id']}").json['rows']) == 1


def test_revocation_blocks_old_link_and_retry(desk, saved):
    ticket = desk.post(f"/api/evidence/{saved['id']}/stations/宁波").json
    link = ticket['download_url']
    assert desk.get(link).status_code == 200
    revoked = desk.post(f"/api/evidence/{saved['id']}/stations/宁波/revoke").json
    assert [(row['id'], row['usable']) for row in revoked['revoked']] == [(ticket['id'], False)]
    assert desk.get(link).status_code == 403
    assert desk.get(f"/api/evidence/ticket/{ticket['token']}/export").status_code == 403
    retry = desk.post(f"/api/evidence/{saved['id']}/stations/宁波").json
    assert (retry['id'], retry['usable'], retry['download_url']) == (ticket['id'], False, None)
    assert len(desk.get(f"/api/evidence/tickets?run={saved['id']}").json['rows']) == 1


def test_unknown_station(desk, saved):
    assert desk.get(f"/api/evidence/{saved['id']}/stations/火星").status_code == 404


def test_issue_matches_station_plan(desk, saved):
    ticket = desk.post(f"/api/evidence/{saved['id']}/stations/宁波").json
    payload = desk.get(ticket['download_url']).json
    assert payload['counts']['manifest'] == payload['ledger']['counts']['manifest']
    assert payload['counts']['manifest'] == 5
    assert [row['line'] for row in payload['rows']] == payload['slices']['scans']['lines']
    assert payload['destination'] == '宁波'


def test_whole_batch_export_unchanged(desk, saved):
    payload = desk.get(f"/api/evidence/{saved['id']}/export").json
    assert payload['originals']['scans.csv'].startswith('﻿')
    assert payload['stages']['ledger']['balanced']


def test_no_other_station_candidates(desk, saved):
    payload = desk.get(f"/api/evidence/{saved['id']}/stations/福州").json
    assert {leg for row in payload['rows'] for leg in row['candidates']} <= {'HX-42'}
    for row in payload['withheld']:
        assert 'HX-41' not in row.get('candidates', [])


def test_revocation_survives_restart(tmp_path):
    from app.main import create_app
    path = tmp_path / 'restart.sqlite3'
    first = create_app(path).test_client()
    saved = first.post('/api/archive', json={'sample': 'dirty'}).json
    ticket = first.post(f"/api/evidence/{saved['id']}/stations/青岛").json
    first.post(f"/api/evidence/{saved['id']}/stations/青岛/revoke")
    second = create_app(path).test_client()
    assert second.get(ticket['download_url']).status_code == 403
    retry = second.post(f"/api/evidence/{saved['id']}/stations/青岛").json
    assert retry['id'] == ticket['id'] and not retry['usable']
