import pytest
from app.errors import DeskError
from app.input import sample
from app.modules.legs.contracts import references
from app.modules.legs.service import associate


# TRAP-23
def test_boundary_handoff(dirty):
    assert next(r for r in dirty['legs']['rows'] if r['event'] == 'E04')['leg'] == 'NX-02'


def test_ambiguous(dirty):
    row, = dirty['legs']['isolated']
    assert (row['reason'], row['candidates']) == ('LEG_AMBIGUOUS', ['HX-41', 'HX-42'])


def test_explicit_hint(dirty):
    assert next(r for r in dirty['legs']['rows'] if r['event'] == 'E07')['leg'] == 'HX-42'


# TRAP-08
def test_tag_preserved(dirty):
    assert dirty['legs']['manifest'][0]['tag'] == '000101'


def test_expired_hint(dirty):
    row = next(r for r in dirty['legs']['rows'] if r['event'] == 'E04')
    assert associate([dict(row, leg_hint='NX-01')], {r['leg']: r for r in dirty['legs']['legs']})['isolated'][0]['reason'] == 'LEG_MISSING'


def test_plan_reference():
    files = sample('clean')
    with pytest.raises(DeskError, match='未知航段'):
        references(files['legs.csv'], files['manifest.csv'].replace('NX-01', 'VOID', 1))
