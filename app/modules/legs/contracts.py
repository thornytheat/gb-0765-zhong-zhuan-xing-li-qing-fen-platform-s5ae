from app.clock import utc
from app.errors import DeskError
from app.modules.scans.csvio import read_table
from app.modules.scans.normalize import SENTINELS


def references(flights, bags):
    legs, isolated = master(flights, ('leg', 'flight', 'start', 'end', 'destination'), 'legs.csv', 'leg')
    manifest, manifest_errors = master(bags, ('tag', 'planned'), 'manifest.csv', 'tag')
    for leg in legs.values():
        try:
            leg['start'], leg['end'] = utc(leg['start']), utc(leg['end'])
            if leg['start'] >= leg['end']:
                raise ValueError('empty window')
        except ValueError as exc:
            raise DeskError('BAD_WINDOW', f"航段 {leg['leg']} 时间窗无效") from exc
    if any(row['planned'] not in legs for row in manifest.values()):
        raise DeskError('BAD_PLAN', '清单引用了未知航段')
    return legs, manifest, isolated + manifest_errors


def master(text, fields, file, key):
    rows, isolated, _ = read_table(text, fields, file)
    indexed = {}
    for row in rows:
        row.update({field: row[field].strip() for field in fields})
        if any(row[field] in SENTINELS for field in fields):
            isolated.append(dict(row, reason='MISSING'))
        elif row[key] in indexed:
            raise DeskError('MASTER_CONFLICT', f"{file} 第 {row['line']} 行主键重复")
        else:
            indexed[row[key]] = row
    if not indexed:
        raise DeskError('NO_MASTER', f'{file} 无可用主数据')
    return indexed, isolated
