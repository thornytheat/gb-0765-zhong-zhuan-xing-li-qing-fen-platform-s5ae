from app.input import sample
from app.pipeline import compute
from app.modules.ledger.service import reconcile


def test_dirty_totals(dirty):
    assert dirty['ledger']['counts'] == dict(manifest=12, loaded=3, pending=8, not_loaded=1, unlisted=1, wrong_bags=2, wrong_legs=2)


def test_clean_totals():
    assert compute(sample('clean'))['ledger']['counts']['loaded'] == 12


def test_leg_subtotals(dirty):
    assert sum(r['manifest'] for r in dirty['ledger']['rows']) == 12


def test_scan_disagreement_blocks_balance(dirty):
    assert not reconcile(dirty['exceptions'], {}, {'balanced': False})['balanced']


def test_default_stage(desk):
    assert desk.get('/api/stage/ledger').json['difference'] == 0


def test_unknown_stage(desk):
    assert desk.get('/api/stage/nope').json['code'] == 'NO_STAGE'
