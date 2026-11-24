
def sequence(rows):
    by_arrival = sorted(rows, key=lambda r: (r['received'], r['line']))
    high_water, prepared = {}, []
    for row in by_arrival:
        key = row['tag'], row['leg']
        effective = row['effective']
        previous = high_water.get(key, effective)
        prepared.append(dict(row, late=effective < previous))
        high_water[key] = max(previous, effective)
    return sorted(prepared, key=lambda r: (r['tag'], r['leg'], r['effective'], r['received'], r['line']))
