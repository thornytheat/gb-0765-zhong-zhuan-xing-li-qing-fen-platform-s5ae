from collections import Counter


def totals(rows, wrong):
    counts = Counter(row['status'] for row in rows)
    return dict(manifest=sum(row['planned'] is not None for row in rows), loaded=counts['loaded'],
                pending=counts['pending'], not_loaded=counts['not_loaded'], unlisted=counts['unlisted'],
                wrong_bags=len({row['tag'] for row in wrong}), wrong_legs=len(wrong))
