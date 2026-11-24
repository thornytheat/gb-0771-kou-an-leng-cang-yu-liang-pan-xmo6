from collections import Counter, defaultdict
from .ledger import capacity


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
    attend = sum(per_lot.values())
    time_diff = attend - exposure['total_seconds']
    position_diff = totals['available'] - totals['occupied'] - totals['frozen'] - totals['free']
    custody_diff = totals['in_stock'] - totals['occupied'] - totals['frozen'] - totals['unplaced']
    conserved = time_diff == custody_diff == 0 and position_diff == -totals['excess'] and all(not r['difference'] for r in lot_seconds)
    return dict(rows=rows, unplaced=pending, counts=totals, lot_seconds=lot_seconds, monitored_seconds=attend,
                time_difference=time_diff, capacity_difference=position_diff, stock_difference=custody_diff,
                balanced=conserved and position_diff == 0, explained=conserved)
