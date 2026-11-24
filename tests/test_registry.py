import pytest
from app.faults import DockFault
from app.modules.registry.service import registry
from app.modules.registry.versions import at, whole
from app.parcels import load_example
from app.utc import second


# TRAP-23

def test_adjacent_versions(dirty):
    data = dirty['registry']['versions']
    point = second('2026-11-21T00:40:00Z')
    assert at(data,'A2',point-1)[0]['door'] == 'EAST'
    assert at(data,'A2',point)[0]['door'] == 'WEST'


def test_unknown_slot(dirty):
    assert at(dirty['registry']['versions'],'X9',0) == (None,'SLOT_UNKNOWN')


def test_no_slot_at_exclusive_end(dirty):
    assert at(dirty['registry']['versions'],'A1',dirty['window']['end']) == (None,'SLOT_UNKNOWN')


def test_overlapping_slot_versions_are_ambiguous():
    files = load_example('dirty')
    files['slots'] += 'A2,03,WEST,8,2026-11-21T00:35:00Z,2026-11-21T00:45:00Z\n'
    parsed = registry(files)
    assert parsed['counts']['overlap'] == 2
    assert at(parsed['versions'],'A2',second('2026-11-21T00:39:00Z')) == (None,'SLOT_AMBIGUOUS')


def test_invalid_piece_count():
    with pytest.raises(ValueError, match='positive integer'):
        whole('1.5')


def test_duplicate_master_key():
    files = load_example('clean')
    files['lots'] += 'F01,9,重复货批\n'
    with pytest.raises(DockFault) as error:
        registry(files)
    assert error.value.code == 'LOT_CONTRACT'
