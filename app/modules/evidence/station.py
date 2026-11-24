"""Per-destination evidence bundles.

A station only receives the rows that back its own conclusions:

* a row whose leg belongs to the station is included in full;
* a row whose leg belongs to another station becomes a redaction stub holding
  the line number and a commitment to its location (never a hash of its
  content), so the conclusion can still be traced without handing over the
  other station's bag record;
* a row whose leg is not decided yet is withheld entirely until the
  attribution is resolved — only its line number and reason are published.

Nothing is silently deleted, so every conclusion keeps a line reference into
the archived originals, and the station's planned-piece count can be re-added
to the ledger figure for that station.
"""
from collections import Counter, defaultdict
from hashlib import sha256

from app.errors import DeskError
from app.manifest import canonical, fingerprint

SCANS = 'scans.csv'


def _digest(value):
    return sha256(canonical(value).encode()).hexdigest()


def _by_line(rows):
    return {row['line']: row for row in rows if row.get('line') is not None}


def _leg_index(stages):
    legs = {row['leg']: row for row in stages['legs']['legs']}
    by_destination = defaultdict(list)
    for leg, row in legs.items():
        by_destination[row['destination']].append(leg)
    return legs, by_destination


def destinations(stages):
    _, by_destination = _leg_index(stages)
    return sorted(by_destination)


def _station_ledger(stages, destination):
    rows = [row for row in stages['ledger']['rows'] if row['destination'] == destination]
    fields = ('manifest', 'loaded', 'pending', 'not_loaded', 'unlisted', 'wrong_bags', 'wrong_legs')
    return rows, {field: sum(row[field] for row in rows) for field in fields}


def _build(result, destination):
    stages = result['stages']
    legs, by_destination = _leg_index(stages)
    own_legs = set(by_destination.get(destination, ()))
    if not own_legs:
        raise DeskError('NO_STATION', '目的站不存在', 404)

    confirmed = _by_line(stages['legs']['rows'])
    unresolved = _by_line(stages['legs']['isolated'])
    rejected = _by_line(stages['scans']['isolated'])
    manifest_rows = [row for row in stages['legs']['manifest'] if row['planned'] in own_legs]
    own_tags = {row['tag'] for row in manifest_rows}
    verdicts = {row['tag']: row for row in stages['exceptions']['rows']}

    dispositions = [dict(verdicts[tag]) for tag in sorted(own_tags) if tag in verdicts]
    # Wrong loads are attributed to the planned leg, exactly like the ledger,
    # so the station's own wrong counts re-add to the ledger's per-leg figures.
    own_wrong = [dict(row) for row in stages['exceptions']['wrong'] if row['planned'] in own_legs]
    # The actual arrival station publishes every wrong load that landed on its
    # own legs; that is where the loading original must be retrievable.
    wrong_here = [dict(row) for row in stages['exceptions']['wrong']
                  if legs.get(row['leg'], {}).get('destination') == destination]

    known_states = defaultdict(list)
    for state in stages['replay']['states']:
        known_states[state['tag']].append(state)
    unlisted = [dict(verdicts[tag]) for tag in sorted(verdicts)
                if verdicts[tag]['status'] == 'unlisted'
                and any(state['leg'] in own_legs for state in known_states.get(tag, ()))]

    rows = sorted((row for row in stages['legs']['rows'] if row['leg'] in own_legs),
                  key=lambda row: row['line'])
    timeline = sorted((row for row in stages['replay']['rows'] if row['leg'] in own_legs),
                      key=lambda row: (row['effective'], row['line']))
    states = [row for row in stages['replay']['states'] if row['leg'] in own_legs]
    # Candidate leg names are part of another station's leg master just as much
    # as its bag rows: keep only this station's own candidates and flag that the
    # flight had more than one.
    for row in rows + timeline:
        candidates = list(row.get('candidates', ()))
        row['candidates'] = [leg for leg in candidates if leg in own_legs]
        row['other_station_candidate'] = len(row['candidates']) != len(candidates)

    redactions, withheld = {}, {}

    def reference(line):
        if line in confirmed:
            if confirmed[line]['leg'] in own_legs:
                return dict(line=line, source=SCANS, kind='included')
            # The redaction keeps a reference into the archive but commits only
            # to the line's location — hashing the raw cells would let the
            # recipient brute-force the other station's bag number.
            redactions[line] = dict(line=line, source=SCANS, reason='OTHER_STATION',
                                    commitment=_digest([result['manifest'].get('id'), SCANS, line]))
            return dict(line=line, source=SCANS, kind='redacted')
        source = unresolved.get(line) or rejected.get(line)
        if source is not None:
            entry = dict(line=line, source=SCANS, reason=source.get('reason') or 'UNRESOLVED')
            candidates = [leg for leg in source.get('candidates', ()) if leg in own_legs]
            if len(candidates) != len(source.get('candidates', ())):
                entry['other_station_candidate'] = True
            if candidates:
                entry['candidates'] = candidates
            withheld[line] = entry
            return dict(line=line, source=SCANS, kind='withheld')
        return dict(line=line, source=SCANS, kind='unknown')

    # The planned station follows this bag's own destination only: no wrong-leg
    # entry is published here.  Confirmed lines on another station's leg become
    # commitment stubs, so the basis of the verdict (e.g. a multi-load) is still
    # traceable by line and hash without handing over the other station's bag
    # record.  The actual arrival station publishes the full original row
    # through ``wrong_loads``/``rows`` below.  Undecided legs stay withheld.
    for row in dispositions:
        row['evidence'] = [reference(line) for line in row.get('source_lines', [])]
        row['wrong_elsewhere'] = bool(row.get('wrong_legs'))
        row['wrong_legs'] = [leg for leg in row.get('wrong_legs', ()) if leg in own_legs]
        row['wrong_elsewhere'] = row['wrong_elsewhere'] and not row['wrong_legs']
    for row in unlisted + wrong_here + own_wrong:
        row['evidence'] = [reference(line) for line in row.get('source_lines', [])]

    # A leg that is still ambiguous affects every station it is a candidate
    # for, even before a planned bag cites it.  The row itself waits behind.
    for row in stages['legs']['isolated']:
        candidates = list(row.get('candidates', ()))
        if row.get('reason') == 'LEG_AMBIGUOUS' and own_legs.intersection(candidates):
            entry = dict(line=row['line'], source=SCANS, reason='LEG_AMBIGUOUS',
                         candidates=sorted(own_legs.intersection(candidates)))
            if len(entry['candidates']) != len(candidates):
                entry['other_station_candidate'] = True
            withheld.setdefault(row['line'], entry)

    status = Counter(row['status'] for row in dispositions)
    planned = len(manifest_rows)
    # Deliberately mirrors the ledger's per-station fields so a recipient can
    # compare piece by piece; redaction/withhold bookkeeping is reported apart.
    # ``planned`` is kept as an alias of ``manifest`` for readers that name the
    # station figure after the plan rather than the ledger column.
    counts = dict(manifest=planned, planned=planned, loaded=status['loaded'],
                  pending=status['pending'], not_loaded=status['not_loaded'],
                  unlisted=len(unlisted),
                  wrong_bags=len({row['tag'] for row in own_wrong}), wrong_legs=len(own_wrong))
    withholding = dict(redacted=len(redactions), withheld=len(withheld))
    # Wrong loads recorded on this station's own legs: the original loading row
    # is retrievable here even though the ledger books the piece against its
    # planned leg elsewhere.
    arrival = dict(wrong_loads=len(wrong_here), wrong_bags=len({row['tag'] for row in wrong_here}))

    station_rows, ledger_counts = _station_ledger(stages, destination)
    fields = ('manifest', 'loaded', 'pending', 'not_loaded')
    matches = all(counts[field] == ledger_counts[field] for field in fields)
    if not matches:
        raise DeskError('EVIDENCE_MISMATCH', '证据件数与对账中的本站计划件数不符', 409)

    def slice_of(source, selected):
        return dict(source=source, lines=sorted(row['line'] for row in selected),
                    sha256=_digest([row['raw'] for row in selected if row.get('raw') is not None]))

    own_manifest = sorted(manifest_rows, key=lambda row: row['line'])
    own_leg_rows = sorted((legs[leg] for leg in own_legs), key=lambda row: row['line'])
    bundle = dict(
        verified=True,
        run=result['manifest'].get('id'),
        version=result['manifest'].get('version'),
        destination=destination,
        legs=[dict(leg=leg, flight=legs[leg]['flight'], destination=legs[leg]['destination'],
                   start=legs[leg]['start'], end=legs[leg]['end']) for leg in sorted(own_legs)],
        manifest=[dict(tag=row['tag'], planned=row['planned'], line=row['line']) for row in own_manifest],
        counts=counts,
        withholding=withholding,
        arrival=arrival,
        ledger=dict(rows=station_rows, counts=ledger_counts),
        reconciliation=dict(manifest=counts['manifest'], ledger_manifest=ledger_counts['manifest'],
                            loaded=counts['loaded'], pending=counts['pending'],
                            not_loaded=counts['not_loaded'], fields=list(fields), balanced=matches),
        rows=rows,
        timeline=timeline,
        states=states,
        dispositions=dispositions,
        wrong_loads=wrong_here,
        unlisted=unlisted,
        redactions=sorted(redactions.values(), key=lambda row: row['line']),
        withheld=sorted(withheld.values(), key=lambda row: row['line']),
        slices=dict(scans=slice_of(SCANS, rows), legs=slice_of('legs.csv', own_leg_rows),
                    manifest=slice_of('manifest.csv', own_manifest)),
        inputs=result['manifest'].get('inputs', {}),
        result_sha256=result['manifest'].get('result_sha256'),
    )
    bundle['bundle_sha256'] = fingerprint(bundle)
    return bundle


def certify_station(files, result, destination):
    from .bundle import certify
    certify(files, result)
    return _build(result, destination)


def summary(files, result, destination):
    return _summary(_build(result, destination))


def _summary(bundle):
    return dict(destination=bundle['destination'],
                legs=[row['leg'] for row in bundle['legs']],
                counts=bundle['counts'], withholding=bundle['withholding'], arrival=bundle['arrival'],
                ledger=bundle['ledger']['counts'], reconciliation=bundle['reconciliation'],
                bundle_sha256=bundle['bundle_sha256'])
