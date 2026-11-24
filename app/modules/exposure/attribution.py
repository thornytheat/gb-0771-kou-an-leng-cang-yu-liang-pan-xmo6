from collections import Counter, defaultdict

KINDS = ('closed', 'warm', 'cooled', 'missing_temp', 'missing_slot', 'missing_door')


def attribute(rows, splits):
    """把每张拆批单归到它结清的那段在库时段，逐时归类却不再重复计入货批总量。

    拆批前后的暴露行由复算按生效时刻切开：实走件对应 `[start, time)` 那段，
    余件从拆批生效起另起一段。两段首尾相接、互不重叠，所以同一段超温只会
    落在其中一处，不会算成两份。若时段被两张单同时认领，重叠秒数记入
    `duplicated`，且不重复累加到任一单的超温。
    """
    by_lot = defaultdict(list)
    for row in rows:
        by_lot[row['lot']].append(row)
    claimed = defaultdict(list)
    result_rows, unattributed, duplicated = [], 0, 0
    for split in sorted(splits, key=lambda row: (row['lot'], row['time'], row['line'])):
        left, right = split['start'], split['time']
        result = Counter({key: 0 for key in KINDS})
        for row in by_lot.get(split['lot'], ()):
            start, end = max(row['start'], left), min(row['end'], right)
            if start >= end:
                continue
            if any(start < done and was < end for was, done in claimed[split['lot']]):
                duplicated += end - start
                continue
            claimed[split['lot']].append((start, end))
            result[row['kind']] += end - start
        covered = sum(result.values())
        unattributed += max(0, right - left - covered)
        result_rows.append(dict(event=split['event'], lot=split['lot'], line=split['line'],
                                time=split['time'], slot=split['slot'], destination=split['destination'],
                                ticket=split['ticket'], total=split['total'], shipped=split['shipped'],
                                remaining=split['remaining'], late=split['late'],
                                attended=right - left, seconds=covered, **dict(result)))
    totals = dict(splits=len(result_rows), shipped=sum(row['shipped'] for row in result_rows),
                  remaining=sum(row['remaining'] for row in result_rows),
                  attended=sum(row['attended'] for row in result_rows),
                  unattributed=unattributed, duplicated=duplicated)
    return result_rows, totals
