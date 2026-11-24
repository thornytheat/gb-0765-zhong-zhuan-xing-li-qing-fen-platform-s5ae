from collections import Counter, defaultdict
from .policy import verdict


def classify(manifest, states, undecided):
    by_tag, issues = defaultdict(dict), defaultdict(list)
    for state in states:
        by_tag[state['tag']][state['leg']] = state
    for row in undecided:
        if row.get('tag') and row.get('action') != 'SORT':
            issues[row['tag']].append(row['line'])
    decisions, wrong = [], []
    for tag in sorted(set(manifest) | by_tag.keys() | issues.keys()):
        row = manifest.get(tag)
        planned = row['planned'] if row else None
        known = by_tag[tag]
        off_plan = sorted(leg for leg, state in known.items() if planned and leg != planned and state['state'] == 'LOADED')
        for leg in off_plan:
            wrong.append(dict(known[leg], planned=planned, reason='WRONG_LEG'))
        disputed = issues[tag] or any(state['state'] == 'CONFLICT' for state in known.values())
        status, reason = verdict(known.get(planned, {}).get('state'), off_plan, disputed) if row else ('unlisted', 'UNLISTED')
        lines = sorted(set(issues[tag]).union(*(state['source_lines'] for state in known.values())))
        decisions.append(dict(tag=tag, planned=planned, manifest_line=row['line'] if row else None,
                              status=status, reason=reason, wrong_legs=off_plan, source_lines=lines))
    return dict(rows=decisions, wrong=wrong, counts=dict(Counter(row['status'] for row in decisions)))
