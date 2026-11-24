from app.parcels import load_example
from app.pipeline import review
from app.modules.capacity.service import reconcile


def test_dirty_stock(dirty):
    assert dirty['capacity']['counts'] == dict(available=27,frozen=4,occupied=4,free=19,excess=0,unplaced=0,in_stock=8)


def test_clean_stock():
    assert review(load_example('clean'))['capacity']['counts']['free'] == 18


def test_conservation(dirty):
    assert dirty['capacity']['balanced'] and dirty['capacity']['monitored_seconds'] == 13800
    assert sum(row['difference'] for row in dirty['capacity']['lot_seconds']) == 0


def test_shrink_reports_excess(dirty):
    registry = dirty['registry']
    registry['versions']['A2'][1]['capacity'] = 3
    result = reconcile(registry,dirty['custody'],dirty['exposure'],dirty['window']['end'])
    assert result['counts']['excess'] == 3 and result['capacity_difference'] == -3
    assert result['explained'] and not result['balanced']


def test_unlocated_pieces_not_silently_counted(dirty):
    dirty['custody']['states']['F03']['slot'] = 'X9'
    result = reconcile(dirty['registry'],dirty['custody'],dirty['exposure'],dirty['window']['end'])
    assert result['counts']['unplaced'] == 2 and result['stock_difference'] == 0


def test_exposure_loss_fails_guard(dirty):
    dirty['exposure']['total_seconds'] -= 60
    result = reconcile(dirty['registry'],dirty['custody'],dirty['exposure'],dirty['window']['end'])
    assert result['time_difference'] == 60 and not result['explained']
