from collections import defaultdict
from itertools import groupby
from .transitions import change, held, split_pieces, split_request


def replay(events, registry, start, end):
    """按生效时刻回放动作；拆批只结清实走件数，余件留在原位继续查验。"""
    states, began, epoch, high = {}, {}, {}, {}
    periods, activity, isolated = [], [], []
    splits, departures = [], []
    entered, released = defaultdict(int), defaultdict(int)
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
                late_row = row['event'] in late
                if issue:
                    isolated.append(dict(row, code=issue))
                    if issue not in ('SLOT_UNKNOWN', 'SLOT_AMBIGUOUS'):
                        continue
                # 缺槽位证据不阻断状态推进：申报槽位照旧占位，件数台账照常结清。
                advanced = issue is None or issue in ('SLOT_UNKNOWN', 'SLOT_AMBIGUOUS')
                previous = states.get(lot)
                before = held(registry, lot, previous) if previous is not None else 0
                if previous is not None and previous != next_state:
                    close(periods, lot, previous, began[lot], moment, start, before)
                if previous != next_state:
                    began[lot] = (moment, row['line'])
                if next_state is None:
                    states.pop(lot, None)
                else:
                    states[lot] = next_state
                if advanced:
                    if row['kind'] == 'IN':
                        entered[lot] += registry['lots'][lot]['pieces']
                        epoch[lot] = (moment, row['line'])
                    elif split_request(row):
                        # 拆批单：只结清实走件数；余件在 next_state 里继续占原槽位。
                        # 声明走满余件时 next_state 为空，余件为 0，仍留一条拆批台账。
                        shipped = split_pieces(row)
                        remaining = next_state.get('remaining', 0) if next_state else 0
                        splits.append(split_row(row, moment, epoch.get(lot, began[lot]),
                                                previous, next_state, before, shipped, remaining,
                                                late_row, start))
                        released[lot] += shipped
                        epoch[lot] = (moment, row['line'])
                    elif row['kind'] == 'OUT':
                        released[lot] += before
                        departures.append(dict(event=row['event'], lot=lot, line=row['line'],
                                               time=moment, pieces=before,
                                               slot=previous['slot'] if previous else None,
                                               ticket=previous['ticket'] if previous else None,
                                               late=late_row))
                        epoch.pop(lot, None)
                activity.append(dict(row, late=late_row, before=previous, after=next_state, code=issue))
    for lot, state in states.items():
        close(periods, lot, state, began[lot], end, start, held(registry, lot, state))
    return dict(rows=activity, periods=periods, states=states, isolated=isolated,
                splits=splits, departures=departures,
                entered=dict(entered), released=dict(released),
                counts=dict(applied=len(activity), late=sum(row['late'] for row in activity),
                            isolated=len(isolated), in_stock=len(states),
                            splits=len(splits), split_pieces=sum(row['shipped'] for row in splits),
                            released_pieces=sum(released.values())))

def split_row(row, moment, opening, previous, next_state, before, shipped, remaining, late, start):
    """拆批台账：实走件数、余件、原槽位、申报去向与查验单一并留证。

    `start` 是这一批件数保持不变的最后起点（入库或上一次拆批），它到本次
    生效时刻之间的暴露即实走件所经历的时段，与余件此后时段首尾相接。
    """
    return dict(event=row['event'], lot=row['lot'], line=row['line'], time=moment,
                start=max(opening[0], start), effective=row['effective'], received=row['received'],
                slot=previous['slot'] if previous else None,
                destination=row.get('slot') or None,
                ticket=previous['ticket'] if previous else None,
                total=before, shipped=shipped, remaining=remaining, late=late,
                before=previous, after=next_state)


def close(periods, lot, state, opening, end, start, pieces):
    left = max(opening[0], start)
    if left < end:
        periods.append(dict(lot=lot, start=left, end=end, source_line=opening[1], pieces=pieces, **state))
