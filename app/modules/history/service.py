from datetime import datetime, timezone
from time import perf_counter_ns
from app.faults import DockFault
from app.pipeline import review
from app.seals import compact, input_seals, sha
from app.settings import VERSION


def save(archive, files):
    begin = perf_counter_ns()
    hashes = input_seals(files)
    key = sha(compact([VERSION, hashes]))
    stages = review(files)
    result = sha(compact(stages))
    stamp = dict(id=key, version=VERSION, inputs=hashes, result_sha256=result, window=stages['window'],
                 elapsed_us=(perf_counter_ns()-begin)//1000, generated_at=datetime.now(timezone.utc).isoformat())
    document, reused = archive.insert(key, stamp, files, stages)
    if document['manifest']['result_sha256'] != result or sha(compact(document['stages'])) != result:
        raise DockFault('DRIFT', '归档与原件复算不一致', 409)
    return dict(brief(document), reused=reused)


def brief(document):
    stamp, stages = document['manifest'], document['stages']
    return dict(id=stamp['id'], manifest=stamp, capacity=stages['capacity']['counts'], exposure=stages['exposure']['counts'])
