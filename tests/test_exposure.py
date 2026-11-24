from app.modules.exposure.doors import signals
from app.modules.exposure.service import classify, slice_period
from app.utc import second


def test_bounce_removed(dirty):
    row = dirty['exposure']['isolated'][0]
    assert (row['code'],row['lines']) == ('DOOR_BOUNCE',[3,4])
    assert dirty['exposure']['doors']['EAST'][1]['time'] == second('2026-11-21T00:10:00Z')


def test_new_version_reassigns_door(dirty):
    switch = second('2026-11-21T00:40:00Z')
    edges = [r for r in dirty['exposure']['rows'] if r['lot']=='F01' and r['slot']=='A2' and (r['start']==switch or r['end']==switch)]
    assert [(r['door'],r['kind']) for r in edges] == [('EAST','closed'),('WEST','cooled')]


def test_ttl_exact_expiry(dirty):
    expired = second('2026-11-21T00:28:00Z')
    assert all(row['kind']=='missing_temp' for row in dirty['exposure']['rows'] if row['door']=='WEST' and row['start']==expired)
    assert sum(row['seconds'] for row in dirty['exposure']['rows'] if row['door']=='WEST' and row['start']==expired) == 240


def test_exact_limit_and_bad_temp(dirty):
    first = dirty['exposure']['temperatures']['WEST'][0]
    assert first['value']=='4.0' and first['warm'] is False
    assert any(row['code']=='TEMP_INVALID' for row in dirty['exposure']['isolated'])


# TRAP-19

def test_priority_keeps_gaps_mutually_exclusive(dirty):
    assert classify('SLOT_UNKNOWN', None, None, 0) == 'missing_slot'
    period = dict(lot='F90',slot='X9',start=0,end=180)
    rows = list(slice_period(period,dirty['registry']['versions'],{},{}))
    assert [(r['kind'],r['seconds']) for r in rows] == [('missing_slot',180)]
    assert classify(None, {'signal':'CLOSED'}, None, 0) == 'closed'


def test_lot_minute_totals(dirty):
    assert dirty['exposure']['counts'] == dict(closed=8100,warm=1800,cooled=2580,missing_temp=420,missing_slot=900,missing_door=0)


def test_door_conflict_order_independent():
    records = [dict(door='A',time=1,line=1,signal='CLOSED'),dict(door='A',time=1,line=2,signal='OPEN')]
    for rows in (records, records[::-1]):
        stable, bad = signals(rows)
        assert stable['A'][0]['signal'] is None and {r['code'] for r in bad} == {'DOOR_CONFLICT'}
