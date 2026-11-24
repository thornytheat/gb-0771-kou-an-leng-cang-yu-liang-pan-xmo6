from app.modules.custody.service import replay
from app.modules.custody.transitions import change


def event(dirty, key):
    return next(row for row in dirty['custody']['rows'] if row['event'] == key)


# TRAP-13

def test_late_seal_before_cancel(dirty):
    seal = event(dirty, 'A06')
    cancel = event(dirty, 'A05')
    assert seal['late'] and seal['after'] == {'slot':'B1','ticket':'H09'}
    assert seal['time'] < cancel['time'] < seal['arrival']


def test_transfer_carries_freeze(dirty):
    assert event(dirty,'A04')['after'] == dict(slot='A2',ticket='H09')


def test_cancel_only_unfreezes(dirty):
    assert event(dirty,'A05')['after'] == dict(slot='A2',ticket=None)


def test_rejected_move_keeps_prior_slot(dirty):
    assert any(row['event']=='D02' and row['code']=='CAPACITY_EXCEEDED' for row in dirty['custody']['isolated'])
    assert event(dirty,'D03')['before']['slot'] == 'A1'


def test_unknown_slot_kept_until_move(dirty):
    assert [(row['slot'], row['end']-row['start']) for row in dirty['custody']['periods'] if row['lot']=='F03'] == [('X9',900),('A1',300),('A1',1800)]


def test_frozen_exit_fails(dirty):
    row = dict(event(dirty,'A05'), kind='OUT')
    assert change(row,{'F01':row['before']},dirty['registry']) == (None,'FROZEN_OUT')


def test_window_end_exclusive(dirty):
    row = dict(event(dirty,'A01'),time=dirty['window']['end'],arrival=dirty['window']['end'])
    assert replay([row],dirty['registry'],**dirty['window'])['counts']['in_stock'] == 0
