import pytest
from app.errors import DeskError
from app.modules.scans.service import ingest


# TRAP-02
def test_bom(dirty):
    assert dirty['scans']['rows'][0]['event'] == 'E01'


# TRAP-04
def test_sections(dirty):
    assert dirty['scans']['counts']['sections'] == 2
    assert dirty['scans']['counts']['source_rows'] == 24


# TRAP-05
def test_bad_width(dirty):
    assert [(r['line'], r['raw'][-1]) for r in dirty['scans']['isolated'] if r['reason'] == 'WIDTH'] == [(21, 'EXTRA')]


# TRAP-07
def test_sentinel(dirty):
    assert dirty['scans']['reasons']['MISSING'] == 1


# TRAP-14
def test_conflicting_id(dirty):
    assert [r['line'] for r in dirty['scans']['isolated'] if r['reason'] == 'ID_CONFLICT'] == [14, 15]


# TRAP-11
def test_equivalent_offset_duplicate(dirty):
    assert [(r['line'], r['effective']) for r in dirty['scans']['repeats']] == [(5, '2026-11-20T16:08:00.000000Z')]


def test_empty_rejected():
    with pytest.raises(DeskError, match='无原件'):
        ingest('')
