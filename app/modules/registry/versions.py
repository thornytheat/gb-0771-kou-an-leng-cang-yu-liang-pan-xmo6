from collections import defaultdict
from app.faults import DockFault
from app.utc import second
from app.modules.intake.csv_rows import rows
from app.modules.intake.contracts import MISSING


def whole(value):
    if not value.isascii() or not value.isdecimal() or len(value) > 8 or not int(value):
        raise ValueError('positive integer required')
    return int(value)


def slot_versions(text):
    accepted, rejected, _ = rows(text, ('slot','revision','door','capacity','from','until'), 'slots')
    if rejected:
        raise DockFault('SLOT_COLUMNS', '槽位存在不齐列')
    versions, ids = defaultdict(list), set()
    for row in accepted:
        try:
            if any(row[key] in MISSING for key in ('slot','revision','door')):
                raise ValueError
            capacity = whole(row['capacity'])
            start, end = second(row['from']), second(row['until'])
            identity = (row['slot'], row['revision'])
            if start >= end or identity in ids:
                raise ValueError
        except ValueError as exc:
            raise DockFault('SLOT_VERSION', f"槽位第 {row['line']} 行无效") from exc
        ids.add(identity)
        versions[row['slot']].append(dict(row, capacity=capacity, start=start, end=end))
    return dict(versions)


def at(versions, slot, time):
    active = [row for row in versions.get(slot, ()) if row['start'] <= time < row['end']]
    if len(active) != 1:
        return None, 'SLOT_AMBIGUOUS' if active else 'SLOT_UNKNOWN'
    return active[0], None
