def test_views_render_all_seven(desk, saved):
    for key, label in [('scans', '扫描原件采信'), ('legs', '航段候选关联'), ('replay', '航段动作序列'),
                       ('exceptions', '错载与漏扫归因'), ('ledger', '件数已对平'),
                       ('archive', '批次留档复跑'), ('evidence', '证据摘要已核验')]:
        result = desk.get(f'/desk/{key}?run={saved["id"]}')
        assert result.status_code == 200 and label in result.get_data(as_text=True)


def test_failure_is_visible(desk):
    result = desk.get('/desk/ledger?sample=unknown')
    assert result.status_code == 404 and '返回清分台' in result.get_data(as_text=True)


def test_scans_can_run_before_bad_master_is_supplied(desk):
    from app.input import sample
    files = dict(sample('dirty'), **{'legs.csv': ''})
    assert desk.post('/api/stage/scans', json={'files': files}).json['counts']['accepted'] == 17
    assert desk.post('/api/stage/legs', json={'files': files}).json['code'] == 'EMPTY_FILE'
    assert desk.get('/api/archive').json['count'] == 0
