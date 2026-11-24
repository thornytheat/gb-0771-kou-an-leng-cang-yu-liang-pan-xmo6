from collections import Counter
from app.modules.registry.versions import at
from .doors import signals
from .temperature import normalize

KINDS = ('closed', 'warm', 'cooled', 'missing_temp', 'missing_slot', 'missing_door')


def exposure(periods, registry, doors, temperatures):
    doors, door_isolation = signals(doors)
    temps, temp_isolation = normalize(temperatures)
    rows = []
    for period in periods:
        rows.extend(slice_period(period, registry['versions'], doors, temps))
    totals = Counter({key: 0 for key in KINDS})
    for row in rows:
        totals[row['kind']] += row['seconds']
    return dict(rows=rows, doors=doors, temperatures=temps, isolated=door_isolation + temp_isolation,
                counts=dict(totals), total_seconds=sum(totals.values()))


def slice_period(period, versions, doors, temps):
    left, right = period['start'], period['end']
    revisions = versions.get(period['slot'], [])
    boundaries = {left, right}
    for version in revisions:
        door = version['door']
        boundaries.update((version['start'], version['end']))
        boundaries.update(row['time'] for row in doors.get(door, []))
        for row in temps.get(door, []):
            boundaries.update((row['time'], row['end']))
    ordered = sorted(point for point in boundaries if left <= point <= right)
    for start, end in zip(ordered, ordered[1:]):
        slot, issue = at(versions, period['slot'], start)
        door = slot['door'] if slot else None
        signal = last_before(doors.get(door, []), start)
        reading = last_before(temps.get(door, []), start)
        kind = classify(issue, signal, reading, start)
        yield dict(period, start=start, end=end, seconds=end-start, door=door, kind=kind,
                   slot_line=slot['line'] if slot else None, door_lines=signal['lines'] if signal else [],
                   temperature_lines=reading['lines'] if reading else [], temperature=reading['value'] if reading and start < reading['end'] else None)


def last_before(values, point):
    return next((row for row in reversed(values) if row['time'] <= point), None)


def classify(issue, signal, reading, start):
    if issue:
        return 'missing_slot'
    if signal is None or signal['signal'] is None:
        return 'missing_door'
    if signal['signal'] == 'CLOSED':
        return 'closed'
    if reading is None or reading['warm'] is None or start >= reading['end']:
        return 'missing_temp'
    return 'warm' if reading['warm'] else 'cooled'
