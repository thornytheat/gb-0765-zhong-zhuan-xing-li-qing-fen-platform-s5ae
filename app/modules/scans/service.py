from collections import Counter, defaultdict
from .csvio import read_table
from .normalize import COLUMNS, normalize


def ingest(text):
    rows, rejected, counts = read_table(text, COLUMNS, 'scans.csv')
    groups = defaultdict(list)
    for raw in rows:
        row, reason = normalize(raw)
        if reason:
            rejected.append(dict(row, reason=reason))
        else:
            groups[row['event']].append(row)
    accepted, duplicates = [], []
    identity = ('tag', 'flight', 'leg_hint', 'action', 'effective')
    for group in groups.values():
        if len({tuple(row[key] for key in identity) for row in group}) > 1:
            rejected.extend(dict(row, reason='ID_CONFLICT') for row in group)
        else:
            ordered = sorted(group, key=lambda row: (row['received'], row['line']))
            accepted.append(ordered[0])
            duplicates.extend(dict(row, reason='RF_REPEAT') for row in ordered[1:])
    counts.update(accepted=len(accepted), duplicates=len(duplicates), rejected=len(rejected))
    counts['balanced'] = counts['source_rows'] == sum(counts[k] for k in ('accepted', 'duplicates', 'rejected', 'blanks')) + counts['sections'] - 1
    return dict(counts=counts, rows=sorted(accepted, key=lambda row: row['line']), isolated=sorted(rejected, key=lambda row: row['line']), repeats=duplicates, reasons=dict(Counter(row['reason'] for row in rejected)))
