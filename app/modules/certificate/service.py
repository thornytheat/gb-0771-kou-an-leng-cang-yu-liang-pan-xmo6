from app.faults import DockFault
from app.seals import compact, input_seals, sha


def issue(document):
    stamp, stages, files = document['manifest'], document['stages'], document['files']
    if (input_seals(files) != stamp['inputs'] or sha(compact(stages)) != stamp['result_sha256'] or
            not stages['capacity']['explained'] or not all(row['balanced'] for row in stages['intake']['counts'].values())):
        raise DockFault('UNCERTIFIED', '原件散列或余量勾稽失败', 409)
    return dict(verified=True, status='reconciled' if stages['capacity']['balanced'] else 'explained_variance', **document)
