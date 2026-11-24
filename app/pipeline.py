from .modules.intake.service import intake
from .modules.registry.service import registry
from .modules.custody.service import replay
from .modules.exposure.service import exposure
from .modules.capacity.service import reconcile
from .window import window


def review(files, until=None):
    if until == 'intake':
        return intake(files)
    if until == 'registry':
        return registry(files)
    start, end = window(files['window'])
    raw = intake(files)
    locations = registry(files)
    custody = replay(raw['tables']['moves'], locations, start, end)
    if until == 'custody':
        return custody
    air = exposure(custody['periods'], locations, raw['tables']['doors'], raw['tables']['temperatures'])
    if until == 'exposure':
        return air
    stock = reconcile(locations, custody, air, end)
    if until == 'capacity':
        return stock
    return dict(window=dict(start=start, end=end), intake=raw, registry=locations, custody=custody, exposure=air, capacity=stock)
