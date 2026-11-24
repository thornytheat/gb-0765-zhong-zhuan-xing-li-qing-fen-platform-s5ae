import pytest
from app.input import sample
from app.main import create_app
from app.pipeline import compute


@pytest.fixture
def desk(tmp_path):
    return create_app(tmp_path / 'test.sqlite3').test_client()


@pytest.fixture
def dirty():
    return compute(sample('dirty'))


@pytest.fixture
def saved(desk):
    return desk.post('/api/archive', json={'sample': 'dirty'}).json
