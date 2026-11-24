from app.modules.registry.versions import at


def held(registry, lot, state):
    """在库件数：拆批后状态只保留余件，未拆过的状态回落到货批主数据。"""
    if state is None:
        return 0
    if 'remaining' in state:
        return state['remaining']
    return registry['lots'][lot]['pieces']


def split_pieces(row):
    """拆批件数：采信层统一写 `shipped`，自建事件也可用 `pieces`/`quantity`/`qty`。

    非法件数抛 ValueError，由调用方转为隔离，不静默按整批处理。
    """
    for key in ('shipped', 'pieces', 'quantity', 'qty'):
        value = row.get(key)
        if value is None or value == '':
            continue
        if isinstance(value, bool):
            raise ValueError('positive integer required')
        text = str(value).strip()
        if not text.isascii() or not text.isdecimal() or not 0 < int(text) < 10 ** 8:
            raise ValueError('positive integer required')
        return int(text)
    return None


def split_request(row):
    """该动作是否为拆批出库（`kind=SPLIT` 或出库单带件数）。"""
    if row['kind'] not in ('OUT', 'SPLIT'):
        return False
    if row['kind'] == 'SPLIT':
        return True
    try:
        return split_pieces(row) is not None
    except ValueError:
        # 件数非法：按拆批处理，由 change 返回 SPLIT_INVALID 隔离，不当作整批出库。
        return True


def carried(current, pieces, slot=None):
    """沿用原状态的查验单与余件，只换槽位（或原位不动）。"""
    state = dict(slot=slot or current['slot'], ticket=current['ticket'])
    if 'remaining' in current:
        state['remaining'] = pieces
    return state


def change(row, states, registry):
    lot, kind, ticket = row['lot'], row['kind'], row['ticket']
    current = states.get(lot)
    if lot not in registry['lots']:
        return None, 'LOT_UNKNOWN'
    if kind == 'IN' and current or kind != 'IN' and current is None:
        return None, 'INVALID_LIFECYCLE'
    if split_request(row):
        remaining = held(registry, lot, current)
        try:
            shipped = split_pieces(row)
        except ValueError:
            return None, 'SPLIT_INVALID'
        if shipped is None:
            return None, 'SPLIT_INVALID'
        if shipped > remaining:
            return None, 'SPLIT_EXCEEDED'
        if shipped == remaining:
            # 声明走满余件即整批出闸，仍受冻结约束；拆批不能绕过 FROZEN_OUT。
            return (None, 'FROZEN_OUT') if current['ticket'] else (None, None)
        # 拆批：只结清实走件数；余件留在原槽位并保持原查验单。
        return dict(slot=current['slot'], ticket=current['ticket'], remaining=remaining - shipped), None
    if kind in ('IN', 'MOVE'):
        slot, issue = at(registry['versions'], row['slot'], row['time'])
        pieces = held(registry, lot, current) if current is not None else registry['lots'][lot]['pieces']
        if slot:
            used = sum(held(registry, name, state) for name, state in states.items()
                       if name != lot and state['slot'] == row['slot'])
            if used + pieces > slot['capacity']:
                return None, 'CAPACITY_EXCEEDED'
        if current is None:
            return dict(slot=row['slot'], ticket=None), issue
        return carried(current, pieces, row['slot']), issue
    if kind == 'OUT':
        return (None, 'FROZEN_OUT') if current['ticket'] else (None, None)
    if kind == 'HOLD':
        return (None, 'ALREADY_FROZEN') if current['ticket'] else (dict(current, ticket=ticket), None)
    if current['ticket'] != ticket:
        return None, 'TICKET_MISMATCH'
    if kind == 'SEAL':
        return current.copy(), None
    return dict(current, ticket=None), None
