from collections import defaultdict
from itertools import groupby
from .transitions import change


def replay(events, registry, start, end):
    states, began, high = {}, {}, {}
    periods, activity, isolated = [], [], []
    late = set()
    for row in sorted(events, key=lambda r: (r['arrival'], r['line'])):
        max_time = high.get(row['lot'], row['time'])
        if row['time'] < max_time:
            late.add(row['event'])
        high[row['lot']] = max(max_time, row['time'])
    ordered = sorted((row for row in events if row['time'] < end), key=lambda r: (r['time'], r['line']))
    for moment, grouped in groupby(ordered, key=lambda row: row['time']):
        by_lot = defaultdict(list)
        for row in grouped:
            by_lot[row['lot']].append(row)
        for lot, batch in sorted(by_lot.items()):
            active = [row for row in batch if row['kind'] != 'SEAL']
            if len(active) > 1:
                isolated.extend(dict(row, code='SIMULTANEOUS') for row in batch)
                continue
            for row in sorted(batch, key=lambda row: (row['kind'] == 'SEAL', row['line'])):
                next_state, issue = change(row, states, registry)
                if issue:
                    isolated.append(dict(row, code=issue))
                    if issue not in ('SLOT_UNKNOWN', 'SLOT_AMBIGUOUS'):
                        continue
                previous = states.get(lot)
                if previous is not None and previous != next_state:
                    close(periods, lot, previous, began[lot], moment, start)
                if previous != next_state:
                    began[lot] = (moment, row['line'])
                if next_state is None:
                    states.pop(lot, None)
                else:
                    states[lot] = next_state
                activity.append(dict(row, late=row['event'] in late, before=previous, after=next_state, code=issue))
    for lot, state in states.items():
        close(periods, lot, state, began[lot], end, start)
    return dict(rows=activity, periods=periods, states=states, isolated=isolated,
                counts=dict(applied=len(activity), late=sum(row['late'] for row in activity),
                            isolated=len(isolated), in_stock=len(states)))


def close(periods, lot, state, opening, end, start):
    left = max(opening[0], start)
    if left < end:
        periods.append(dict(lot=lot, start=left, end=end, source_line=opening[1], **state))
