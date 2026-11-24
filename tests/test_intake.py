import pytest
from app.faults import DockFault
from app.modules.intake.csv_rows import rows


# TRAP-02

def test_bom_column(dirty):
    assert dirty['intake']['tables']['moves'][0]['event'] == 'A01'


# TRAP-04

def test_repeated_header(dirty):
    assert dirty['intake']['counts']['moves']['repeated_headers'] == 1
    assert dirty['intake']['counts']['moves']['total'] == 23


# TRAP-05, TRAP-07

def test_width_and_sentinel(dirty):
    isolated = [(r['line'], r['code']) for r in dirty['intake']['isolated']]
    assert (22,'MISSING') in isolated and (23,'WIDTH') in isolated


# TRAP-11

def test_offset_equivalence(dirty):
    repeated, = dirty['intake']['copies']
    first = next(r for r in dirty['intake']['tables']['moves'] if r['event']=='E02')
    assert repeated['line'] == 19 and first['time'] == repeated['time']


# TRAP-14

def test_conflicting_packet(dirty):
    assert [r['ticket'] for r in dirty['intake']['isolated'] if r['code']=='EVENT_CONFLICT'] == ['H19','H91']


def test_broken_header():
    with pytest.raises(DockFault) as error:
        rows('typo\n', ('name',), 'lot')
    assert error.value.code == 'HEADER'


def test_input_conservation(dirty):
    assert dirty['intake']['counts']['moves'] == dict(total=23,blanks=1,repeated_headers=1,accepted=16,isolated=4,duplicates=1,balanced=True)
