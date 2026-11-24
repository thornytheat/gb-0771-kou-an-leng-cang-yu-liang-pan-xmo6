from .faults import DockFault
from .settings import EXAMPLES, PARTS


def load_example(name):
    if name not in ('dirty', 'clean'):
        raise DockFault('NO_SAMPLE', '找不到口岸样例', 404)
    ext = {part: 'json' if part == 'window' else 'csv' for part in PARTS}
    return {part: (EXAMPLES / name / f'{part}.{ext[part]}').read_bytes().decode() for part in PARTS}


def receive_pack(body):
    if isinstance(body, dict) and set(body) == {'sample'}:
        return load_example(body['sample'])
    if isinstance(body, dict) and set(body) == set(PARTS) and all(isinstance(x, str) for x in body.values()):
        return body
    raise DockFault('BAD_PACK', '提交样例或完整六份原件')
