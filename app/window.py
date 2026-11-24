import json
from .faults import DockFault
from .utc import second


def window(raw):
    try:
        values = json.loads(raw)
        if set(values) != {'from', 'until'}:
            raise ValueError
        start, end = second(values['from']), second(values['until'])
        if end <= start or end-start > 7 * 86400:
            raise ValueError
        return start, end
    except (TypeError, ValueError, KeyError) as exc:
        raise DockFault('WINDOW', '查验窗口须为带偏移的有效区间') from exc
