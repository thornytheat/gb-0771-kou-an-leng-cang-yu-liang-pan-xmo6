from collections import Counter, defaultdict
from .ledger import capacity

KINDS = ('closed', 'warm', 'cooled', 'missing_temp', 'missing_slot', 'missing_door')


def reconcile(registry, custody, exposure, end):
    rows, pending, totals = capacity(registry, custody['states'], end-1)
    exposure_by_lot = defaultdict(Counter)
    for row in exposure['rows']:
        exposure_by_lot[row['lot']][row['kind']] += row['seconds']
    per_lot = Counter()
    for period in custody['periods']:
        per_lot[period['lot']] += period['end'] - period['start']
    lot_seconds = [dict(lot=lot, attended=seconds, **result, difference=seconds-sum(result.values()))
                   for lot, seconds in sorted(per_lot.items()) for result in [exposure_by_lot[lot]]]
    splits = exposure.get('splits', [])
    split_totals = exposure.get('split_totals', dict(splits=0, shipped=0, remaining=0, attended=0,
                                                     unattributed=0, duplicated=0))
    attend = sum(per_lot.values())
    time_diff = attend - exposure['total_seconds']
    position_diff = totals['available'] - totals['occupied'] - totals['frozen'] - totals['free']
    custody_diff = totals['in_stock'] - totals['occupied'] - totals['frozen'] - totals['unplaced']
    pieces = piece_balance(registry, custody, totals)
    conserved = (time_diff == custody_diff == 0 and position_diff == -totals['excess']
                 and all(not r['difference'] for r in lot_seconds)
                 and split_totals['unattributed'] == 0 and split_totals['duplicated'] == 0
                 and pieces['difference'] == 0)
    return dict(rows=rows, unplaced=pending, counts=totals, lot_seconds=lot_seconds, monitored_seconds=attend,
                time_difference=time_diff, capacity_difference=position_diff, stock_difference=custody_diff,
                splits=splits, split_totals=split_totals, pieces=pieces,
                balanced=conserved and position_diff == 0, explained=conserved)


def piece_balance(registry, custody, totals):
    """件数勾稽：入库 - 拆走出闸 - 整批出库 = 收盘在库余件。"""
    entered = sum(custody.get('entered', {}).values())
    released = sum(custody.get('released', {}).values())
    return dict(entered=entered, released=released, in_stock=totals['in_stock'],
                difference=entered-released-totals['in_stock'])
