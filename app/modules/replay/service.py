from itertools import groupby
from .radio import sequence


def replay(rows):
    timeline, states, conflicts, repeats = [], [], [], []
    for (tag, leg), stream in groupby(sequence(rows), key=lambda r: (r['tag'], r['leg'])):
        state, sources = 'UNSEEN', []
        for _, same_time in groupby(stream, key=lambda r: r['effective']):
            group = list(same_time)
            motions = {r['action'] for r in group} - {'SORT'}
            before = state
            if len(motions) == 2:
                state = 'CONFLICT'
                conflicts.extend(dict(r, reason='SIMULTANEOUS') for r in group if r['action'] in motions)
            elif motions:
                state = 'LOADED' if 'LOAD' in motions else 'OFFLOADED'
            sources.extend(r['line'] for r in group)
            seen = set()
            for r in group:
                if r['action'] in seen:
                    repeats.append(dict(r, reason='RF_REPEAT'))
                else:
                    timeline.append(dict(r, before=before, after=state))
                seen.add(r['action'])
        states.append(dict(tag=tag, leg=leg, state=state, source_lines=sources))
    return dict(rows=timeline, states=states, isolated=conflicts, repeats=repeats,
                counts=dict(late=sum(row['late'] for row in timeline), states=len(states), conflicts=len(conflicts)))
