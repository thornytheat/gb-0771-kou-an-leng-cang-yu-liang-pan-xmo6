from collections import defaultdict
from app.modules.registry.versions import at


def held(registry, lot, state):
    """在库件数：拆批后状态只留余件，未拆过的状态回落到货批主数据。"""
    if 'remaining' in state:
        return state['remaining']
    return registry['lots'][lot]['pieces']


def capacity(registry, states, moment):
    buckets = defaultdict(list)
    for lot, state in sorted(states.items()):
        buckets[state['slot']].append(dict(lot=lot, pieces=held(registry, lot, state),
                                           total=registry['lots'][lot]['pieces'],
                                           frozen=bool(state['ticket']),
                                           line=state.get('line')))
    rows, pending = [], []
    for slot in sorted(set(registry['versions']) | set(buckets)):
        version, code = at(registry['versions'], slot, moment)
        items = buckets[slot]
        if version is None:
            pending.extend(dict(row, slot=slot, code=code) for row in items)
            continue
        frozen = sum(row['pieces'] for row in items if row['frozen'])
        occupied = sum(row['pieces'] for row in items if not row['frozen'])
        available = version['capacity']
        rows.append(dict(slot=slot, door=version['door'], version=version['revision'], source_line=version['line'],
                         lots=items, available=available, frozen=frozen, occupied=occupied,
                         free=max(0, available-frozen-occupied), excess=max(0, occupied+frozen-available)))
    totals = {field: sum(row[field] for row in rows) for field in ('available','frozen','occupied','free','excess')}
    totals['unplaced'] = sum(row['pieces'] for row in pending)
    totals['in_stock'] = sum(held(registry, lot, state) for lot, state in states.items())
    return rows, pending, totals
