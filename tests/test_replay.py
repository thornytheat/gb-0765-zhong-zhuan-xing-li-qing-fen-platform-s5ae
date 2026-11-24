from app.modules.replay.service import replay


# TRAP-13
def test_late_offload_before_reload(dirty):
    rows = [r for r in dirty['replay']['rows'] if r['tag'] == '000101']
    assert [(r['event'], r['late'], r['after']) for r in rows] == [('E01', False, 'LOADED'), ('E02', True, 'OFFLOADED'), ('E03', False, 'LOADED')]


def test_offload_does_not_clear_other_leg(dirty):
    assert [(r['leg'], r['state']) for r in dirty['replay']['states'] if r['tag'] == '000102'] == [('NX-01', 'OFFLOADED'), ('NX-02', 'LOADED')]


def test_same_time_conflict(dirty):
    assert [r['line'] for r in dirty['replay']['isolated']] == [12, 13]


def test_radio_repeat_other_id(dirty):
    assert [r['event'] for r in dirty['replay']['repeats']] == ['E20']


def test_sort_is_not_load(dirty):
    assert next(r for r in dirty['replay']['states'] if r['tag'] == '000109')['state'] == 'UNSEEN'


def test_empty_stream():
    assert replay([])['counts'] == {'late': 0, 'states': 0, 'conflicts': 0}
