from collections import defaultdict
from app.settings import MIN_DOOR_PULSE


def signals(rows):
    grouped = defaultdict(lambda: defaultdict(list))
    for row in rows:
        grouped[row['door']][row['time']].append(row)
    history, isolated = {}, []
    for door, timestamps in sorted(grouped.items()):
        sequence = []
        for moment, group in sorted(timestamps.items()):
            states = {row['signal'] for row in group}
            signal = next(iter(states)) if len(states) == 1 else None
            if signal is None:
                isolated.extend(dict(row, code='DOOR_CONFLICT') for row in group)
            if sequence and signal == sequence[-1]['signal']:
                continue
            sequence.append(dict(time=moment, signal=signal, lines=[row['line'] for row in group]))
        stable = []
        for row in sequence:
            if stable and stable[-1]['signal'] == row['signal']:
                continue
            if (len(stable) >= 2 and stable[-2]['signal'] == row['signal'] and row['signal'] is not None and
                    stable[-1]['signal'] is not None and row['time'] - stable[-1]['time'] < MIN_DOOR_PULSE):
                pulse = stable.pop()
                isolated.append(dict(code='DOOR_BOUNCE', door=door, time=pulse['time'], lines=pulse['lines'] + row['lines']))
            else:
                stable.append(row)
        history[door] = stable
    return history, isolated
