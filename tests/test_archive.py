from concurrent.futures import ThreadPoolExecutor
from app.input import sample
from app.modules.archive.service import archive
from app.modules.archive.store import Archive
from app.pipeline import compute


def test_rerun(desk, saved):
    again = desk.post(f"/api/archive/{saved['id']}/rerun").json
    assert again['reused'] and again['manifest'] == saved['manifest']


def test_same_input(desk, saved):
    assert desk.post('/api/archive', json={'files': sample('dirty')}).json['id'] == saved['id']
    assert desk.get('/api/archive').json['count'] == 1


def test_different_input(desk, saved):
    assert desk.post('/api/archive', json={'sample': 'clean'}).json['id'] != saved['id']


def test_missing(desk):
    result = desk.post('/api/archive/unknown/rerun')
    assert (result.status_code, result.json['code']) == (404, 'NO_RUN')


def test_atomic_invalid_master(desk):
    files = dict(sample('dirty'), **{'manifest.csv': ''})
    assert desk.post('/api/archive', json={'files': files}).status_code == 422
    assert desk.get('/api/archive').json['count'] == 0


def test_concurrent(tmp_path):
    store = Archive(tmp_path / 'parallel.sqlite3')
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: archive(store, sample('dirty'), compute), range(4)))
    assert sum(not result['reused'] for result in results) == 1
    assert len({result['id'] for result in results}) == len(store.list()) == 1


def test_reopen_same_archive(tmp_path, saved):
    from app.main import create_app
    result = create_app(tmp_path / 'test.sqlite3').test_client().get(f"/api/archive/{saved['id']}")
    assert result.json['manifest'] == saved['manifest'] and result.json['counts']['pending'] == 8
