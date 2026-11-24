from collections import defaultdict


def associate(rows, legs):
    by_flight = defaultdict(list)
    for leg in legs.values():
        by_flight[leg['flight']].append(leg)
    linked, isolated = [], []
    for row in rows:
        candidates = sorted(
            leg['leg'] for leg in by_flight[row['flight']]
            if leg['start'] <= row['effective'] < leg['end']
        )
        chosen = [leg for leg in candidates if row['leg_hint'] in (None, leg)]
        evidence = dict(row, candidates=candidates)
        if len(chosen) == 1:
            linked.append(dict(evidence, leg=chosen[0]))
        else:
            isolated.append(dict(evidence, reason='LEG_AMBIGUOUS' if chosen else 'LEG_MISSING'))
    return dict(rows=linked, isolated=isolated, counts=dict(linked=len(linked), unresolved=len(isolated)))
