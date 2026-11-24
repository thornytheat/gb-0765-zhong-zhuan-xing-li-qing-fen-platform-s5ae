from app.clock import utc

COLUMNS = ('event', 'tag', 'flight', 'leg_hint', 'action', 'effective', 'received')
SENTINELS = {'', '-', 'N/A', 'NULL', '未知'}
ACTIONS = {'SORT', 'LOAD', 'OFFLOAD'}


def normalize(record):
    row = record.copy()
    for field in COLUMNS:
        row[field] = row[field].strip()
    if any(row[field] in SENTINELS for field in COLUMNS if field != 'leg_hint'):
        return row, 'MISSING'
    row['leg_hint'] = None if row['leg_hint'] in SENTINELS else row['leg_hint']
    if row['action'] not in ACTIONS:
        return row, 'ACTION'
    try:
        row['effective'], row['received'] = utc(row['effective']), utc(row['received'])
    except ValueError:
        return row, 'TIME'
    if row['received'] < row['effective']:
        return row, 'TIME'
    return row, None
