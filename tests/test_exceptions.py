def find(dirty, tag):
    return next(r for r in dirty['exceptions']['rows'] if r['tag'] == tag)


def test_ambiguous_evidence_is_pending(dirty):
    assert find(dirty, '000103')['source_lines'] == [8]
    assert find(dirty, '000103')['reason'] == 'UNCERTAIN'


def test_offloaded(dirty):
    assert find(dirty, '000104')['status'] == 'not_loaded'


def test_sort_missing(dirty):
    assert find(dirty, '000109')['reason'] == 'NO_LOAD'


def test_multi_loaded(dirty):
    assert find(dirty, '000108')['reason'] == 'MULTI_LOADED'


def test_wrong_leg_is_separate(dirty):
    assert [(r['tag'], r['leg']) for r in dirty['exceptions']['wrong']] == [('000105', 'NX-01'), ('000108', 'NX-02')]


def test_unlisted(dirty):
    assert find(dirty, '009999')['status'] == 'unlisted'
