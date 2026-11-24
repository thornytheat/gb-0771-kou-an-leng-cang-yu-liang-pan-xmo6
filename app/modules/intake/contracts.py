from app.utc import second

COLUMNS = {
    'moves': ('event', 'lot', 'kind', 'slot', 'ticket', 'effective', 'received'),
    'doors': ('door', 'signal', 'effective'),
    'temperatures': ('door', 'celsius', 'effective'),
}
# 附加列整列可缺席，老原件照常采信。`pieces` 仅用于拆批出库，声明本次
# 实际出闸件数；整批出库留空。`quantity`/`qty` 是同一语义的别名，便于
# 交接原件沿用各自表头。
OPTIONAL = {'moves': ('pieces', 'quantity', 'qty')}
QUANTITY = ('pieces', 'quantity', 'qty')
MISSING = {'', '-', 'N/A', 'NULL', '未知'}
MOVES = {'IN', 'MOVE', 'OUT', 'HOLD', 'RELEASE', 'CANCEL', 'SEAL', 'SPLIT'}


def quantity(value):
    """拆批件数：正整数，最多八位。"""
    if isinstance(value, bool):
        raise ValueError('positive integer required')
    if isinstance(value, int):
        if not 0 < value < 10 ** 8:
            raise ValueError('positive integer required')
        return value
    if not isinstance(value, str) or not value.isascii() or not value.isdecimal() \
            or len(value) > 8 or not int(value):
        raise ValueError('positive integer required')
    return int(value)


def declared(row):
    """该动作腾挪的件数：拆批单写明实走件；整批单返回 None。"""
    for key in QUANTITY:
        value = row.get(key)
        if value is None or (isinstance(value, str) and value in MISSING):
            continue
        return quantity(value)
    return None


def normalize(row):
    source = row['source']
    required = set(COLUMNS[source]) - {'slot', 'ticket'}
    if any(row[key] in MISSING for key in required):
        return 'MISSING'
    if source == 'moves' and (row['kind'] not in MOVES or
            (row['kind'] in ('IN', 'MOVE') and row['slot'] in MISSING) or
            (row['kind'] in ('HOLD', 'CANCEL', 'RELEASE', 'SEAL') and row['ticket'] in MISSING)):
        return 'MOVE_FIELDS'
    if source == 'moves':
        try:
            shipped = declared(row)
        except ValueError:
            return 'SPLIT_INVALID'
        if shipped is not None and row['kind'] not in ('OUT', 'SPLIT'):
            # 只有出库/拆批能声明件数；其余动作带该列会造成去向歧义。
            return 'SPLIT_INVALID'
        if row['kind'] == 'SPLIT' and shipped is None:
            # 拆批单必须写明实走件数，否则无从结清。
            return 'SPLIT_INVALID'
        row['shipped'] = shipped
    if source == 'doors' and row['signal'] not in ('OPEN', 'CLOSED'):
        return 'SIGNAL'
    try:
        row['time'] = second(row['effective'])
        if source == 'moves':
            row['arrival'] = second(row['received'])
            if row['arrival'] < row['time']:
                return 'TIME'
    except ValueError:
        return 'TIME'
    return None
