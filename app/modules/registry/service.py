from itertools import combinations
from app.faults import DockFault
from app.modules.intake.contracts import MISSING
from app.modules.intake.csv_rows import rows
from .versions import slot_versions, whole


def registry(files):
    versions = slot_versions(files['slots'])
    raw, rejected, _ = rows(files['lots'], ('lot','pieces','description'), 'lots')
    lots = {}
    for row in raw:
        try:
            if row['lot'] in MISSING or row['lot'] in lots or row['description'] in MISSING:
                raise ValueError
            size = whole(row['pieces'])
        except ValueError as exc:
            raise DockFault('LOT_CONTRACT', f"货批第 {row['line']} 行无效") from exc
        lots[row['lot']] = dict(row, pieces=size)
    if rejected or not lots or not versions:
        raise DockFault('REGISTRY_INCOMPLETE', '货批或槽位主数据不完整')
    conflicts = []
    for slot, revisions in versions.items():
        for left, right in combinations(revisions, 2):
            start, end = max(left['start'], right['start']), min(left['end'], right['end'])
            if start < end:
                conflicts.append(dict(slot=slot, start=start, end=end, code='SLOT_AMBIGUOUS', lines=[left['line'], right['line']]))
    return dict(versions=versions, lots=lots, isolated=conflicts,
                counts=dict(lots=len(lots), slots=len(versions), revisions=sum(map(len, versions.values())), overlap=len(conflicts)))
