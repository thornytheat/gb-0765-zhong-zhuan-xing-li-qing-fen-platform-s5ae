from .tally import totals


def reconcile(decisions, legs, scan_counts):
    rows, wrong = decisions['rows'], decisions['wrong']
    counts = totals(rows, wrong)
    by_leg = [dict(leg=leg, destination=leg_row['destination'], **totals(
        [row for row in rows if row['planned'] == leg], [row for row in wrong if row['planned'] == leg]
    )) for leg, leg_row in sorted(legs.items())]
    balance = counts['manifest'] - counts['loaded'] - counts['pending'] - counts['not_loaded']
    return dict(counts=counts, balanced=balance == 0 and scan_counts['balanced'], difference=balance, rows=by_leg)
