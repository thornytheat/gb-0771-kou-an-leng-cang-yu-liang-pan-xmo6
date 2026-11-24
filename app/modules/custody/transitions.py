from app.modules.registry.versions import at


def change(row, states, registry):
    lot, kind, ticket = row['lot'], row['kind'], row['ticket']
    current = states.get(lot)
    if lot not in registry['lots']:
        return None, 'LOT_UNKNOWN'
    if kind == 'IN' and current or kind != 'IN' and current is None:
        return None, 'INVALID_LIFECYCLE'
    if kind in ('IN', 'MOVE'):
        slot, issue = at(registry['versions'], row['slot'], row['time'])
        if slot:
            used = sum(registry['lots'][name]['pieces'] for name, state in states.items()
                       if name != lot and state['slot'] == row['slot'])
            if used + registry['lots'][lot]['pieces'] > slot['capacity']:
                return None, 'CAPACITY_EXCEEDED'
        return dict(slot=row['slot'], ticket=current['ticket'] if current else None), issue
    if kind == 'OUT':
        return (None, 'FROZEN_OUT') if current['ticket'] else (None, None)
    if kind == 'HOLD':
        return (None, 'ALREADY_FROZEN') if current['ticket'] else (dict(current, ticket=ticket), None)
    if current['ticket'] != ticket:
        return None, 'TICKET_MISMATCH'
    if kind == 'SEAL':
        return current.copy(), None
    return dict(current, ticket=None), None
