"""拆批出库：按实际件数结清余量，余件留原位并保查验，暴露不重复计数。"""
from app.labels import CODES
from app.pipeline import review
from app.utc import second

WINDOW = '{"from":"2026-11-21T00:00:00Z","until":"2026-11-21T02:00:00Z"}'
HEAD = 'event,lot,kind,slot,ticket,effective,received,pieces'

SLOTS = """slot,revision,door,capacity,from,until
A1,01,EAST,20,2026-11-21T00:00:00Z,2026-11-21T02:00:00Z
B1,01,WEST,20,2026-11-21T00:00:00Z,2026-11-21T02:00:00Z
"""

LOTS = """lot,pieces,description
F01,5,鳕鱼箱
F02,3,冻豌豆
"""

DOORS = """door,signal,effective
EAST,OPEN,2026-11-21T00:00:00Z
WEST,CLOSED,2026-11-21T00:00:00Z
"""

TEMPS = """door,celsius,effective
EAST,6.0,2026-11-21T00:00:00Z
WEST,2.0,2026-11-21T00:00:00Z
"""

# 每 600 秒续一条同温读数，保证整段窗口都在有效期内，超温时段不被温度缺证截断。
WARM = ("door,celsius,effective\n" +
        "".join(f"EAST,6.0,2026-11-21T{minute // 60:02d}:{minute % 60:02d}:00Z\n"
                for minute in range(0, 120, 10)))


def pack(moves, *, lots=LOTS, slots=SLOTS, doors=DOORS, temperatures=TEMPS, window=WINDOW):
    """构造原件：行可省略末尾 pieces 列，由这里补齐成与表头等宽。"""
    body = moves if moves.startswith('event') else HEAD + '\n' + moves
    header, *lines = body.splitlines()
    width = len(header.split(','))
    padded = [line if line.count(',') + 1 == width else line + ',' * (width - line.count(',') - 1)
              for line in lines]
    return dict(moves='\n'.join([header] + padded) + '\n', slots=slots, doors=doors,
                temperatures=temperatures, lots=lots, window=window)


# --- 件数结清与余件留位 -------------------------------------------------------

def test_split_out_settles_only_shipped_pieces():
    stages = review(pack('S1,F01,IN,A1,,2026-11-21T00:10:00Z,2026-11-21T00:10:00Z\n'
                         'S2,F01,OUT,,,2026-11-21T00:30:00Z,2026-11-21T00:30:00Z,2\n'))
    custody, stock = stages['custody'], stages['capacity']
    # 余件仍在原槽位：A1 占 3 件，B1 为 0
    assert custody['states']['F01'] == dict(slot='A1', ticket=None, remaining=3)
    assert stock['counts']['occupied'] == 3
    assert stock['counts']['in_stock'] == 3
    assert stock['counts']['free'] == 37 and stock['balanced']
    rows = {row['slot']: row for row in stock['rows']}
    assert rows['A1']['lots'][0]['pieces'] == 3
    assert stock['pieces'] == dict(entered=5, released=2, in_stock=3, difference=0)


def test_remainder_keeps_original_slot_and_can_be_held():
    # 先拆走两件，留下的三件继续占原槽位；随后查验冻结落在余件上。
    stages = review(pack('S1,F01,IN,A1,,2026-11-21T00:10:00Z,2026-11-21T00:10:00Z\n'
                         'S2,F01,OUT,,,2026-11-21T00:20:00Z,2026-11-21T00:20:00Z,2\n'
                         'S3,F01,HOLD,,H09,2026-11-21T00:30:00Z,2026-11-21T00:30:00Z\n'))
    state = stages['custody']['states']['F01']
    assert state == dict(slot='A1', ticket='H09', remaining=3)
    # 冻结只覆盖留下的三件，拆走的两件不再计冻结
    assert stages['capacity']['counts']['frozen'] == 3
    assert stages['capacity']['counts']['in_stock'] == 3


def test_split_ledger_records_destination_and_ticket():
    stages = review(pack('S1,F01,IN,A1,,2026-11-21T00:10:00Z,2026-11-21T00:10:00Z\n'
                         'S2,F01,HOLD,,H09,2026-11-21T00:15:00Z,2026-11-21T00:15:00Z\n'
                         'S3,F01,CANCEL,,H09,2026-11-21T00:20:00Z,2026-11-21T00:20:00Z\n'
                         'S4,F01,OUT,B1,,2026-11-21T00:40:00Z,2026-11-21T00:40:00Z,2\n'))
    split, = stages['custody']['splits']
    assert (split['event'], split['shipped'], split['remaining']) == ('S4', 2, 3)
    assert split['slot'] == 'A1' and split['destination'] == 'B1'
    assert split['total'] == 5
    assert stages['custody']['counts']['splits'] == 1
    assert stages['custody']['counts']['released_pieces'] == 2


def test_next_lot_can_take_the_freed_capacity():
    stages = review(pack(
        'S1,F01,IN,A1,,2026-11-21T00:10:00Z,2026-11-21T00:10:00Z\n'
        'S2,F02,IN,A1,,2026-11-21T00:15:00Z,2026-11-21T00:15:00Z\n'
        'S3,F01,OUT,,,2026-11-21T00:30:00Z,2026-11-21T00:30:00Z,2\n'
        'S4,F02,MOVE,A1,,2026-11-21T00:45:00Z,2026-11-21T00:45:00Z\n',
        slots='slot,revision,door,capacity,from,until\n'
              'A1,01,EAST,8,2026-11-21T00:00:00Z,2026-11-21T02:00:00Z\n'))
    # 余件 3 + F02 3 = 6 ≤ 8，调入不撞上还在的三件
    assert not stages['custody']['isolated']
    assert stages['custody']['states']['F02']['slot'] == 'A1'
    assert stages['capacity']['counts']['occupied'] == 6


def test_split_exceeding_remaining_is_isolated_and_keeps_state():
    stages = review(pack('S1,F01,IN,A1,,2026-11-21T00:10:00Z,2026-11-21T00:10:00Z\n'
                         'S2,F01,OUT,,,2026-11-21T00:30:00Z,2026-11-21T00:30:00Z,9\n'))
    assert [(row['event'], row['code']) for row in stages['custody']['isolated']] == [('S2', 'SPLIT_EXCEEDED')]
    assert stages['custody']['states']['F01'] == dict(slot='A1', ticket=None)


def test_split_of_remainder_must_not_bypass_freeze():
    stages = review(pack('S1,F01,IN,A1,,2026-11-21T00:10:00Z,2026-11-21T00:10:00Z\n'
                         'S2,F01,HOLD,,H09,2026-11-21T00:20:00Z,2026-11-21T00:20:00Z\n'
                         'S3,F01,OUT,,,2026-11-21T00:30:00Z,2026-11-21T00:30:00Z,5\n'))
    assert [(row['event'], row['code']) for row in stages['custody']['isolated']] == [('S3', 'FROZEN_OUT')]
    assert stages['custody']['states']['F01']['ticket'] == 'H09'


def test_pieces_column_is_optional_for_whole_out():
    stages = review(pack('S1,F01,IN,A1,,2026-11-21T00:10:00Z,2026-11-21T00:10:00Z\n'
                         'S2,F01,OUT,,,2026-11-21T00:30:00Z,2026-11-21T00:30:00Z\n'))
    assert 'F01' not in stages['custody']['states']
    assert stages['custody']['departures'][0]['pieces'] == 5
    assert stages['capacity']['counts']['occupied'] == 0


def test_pieces_on_non_out_action_is_isolated():
    stages = review(pack('S1,F01,IN,A1,,2026-11-21T00:10:00Z,2026-11-21T00:10:00Z\n'
                         'S2,F01,HOLD,,H09,2026-11-21T00:20:00Z,2026-11-21T00:20:00Z,2\n'))
    assert [(row['event'], row['code']) for row in stages['intake']['isolated']] == [('S2', 'SPLIT_INVALID')]


# --- 超温不因拆批算成两份 -----------------------------------------------------

def test_split_exposure_is_not_double_counted():
    stages = review(pack('S1,F01,IN,A1,,2026-11-21T00:10:00Z,2026-11-21T00:10:00Z\n'
                         'S2,F01,OUT,,,2026-11-21T01:10:00Z,2026-11-21T01:10:00Z,2\n',
                         doors='door,signal,effective\nEAST,OPEN,2026-11-21T00:00:00Z\n',
                         temperatures=WARM))
    rows = [row for row in stages['exposure']['rows'] if row['lot'] == 'F01']
    # 00:10 入库到 02:00 收盘共 6600 秒，拆走 2 件后 3 件仍留库内
    assert sum(row['seconds'] for row in rows) == 6600
    assert stages['exposure']['counts']['warm'] == 6600
    assert stages['capacity']['time_difference'] == 0
    split, = stages['capacity']['splits']
    # 拆批只认领 00:10-01:10 这段 3600 秒，余件此后另起一段，不重算
    assert split['seconds'] == split['attended'] == 3600 and split['warm'] == 3600
    assert stages['capacity']['split_totals']['duplicated'] == 0
    assert stages['capacity']['split_totals']['unattributed'] == 0


def test_split_attribution_splits_single_warm_window_at_effective_time():
    stages = review(pack('S1,F01,IN,A1,,2026-11-21T00:00:00Z,2026-11-21T00:00:00Z\n'
                         'S2,F01,OUT,,,2026-11-21T01:00:00Z,2026-11-21T01:00:00Z,2\n',
                         doors='door,signal,effective\nEAST,OPEN,2026-11-21T00:00:00Z\n',
                         temperatures=WARM))
    split, = stages['capacity']['splits']
    # 00:00-01:00 归实走件，01:00-02:00 归余件；两个区间首尾相接、互不重叠，
    # 合计正好等于一次连续超温 7200 秒，没有一段被算成两份
    assert split['warm'] == 3600 and split['attended'] == 3600
    remainder = [row for row in stages['exposure']['rows']
                 if row['lot'] == 'F01' and row['start'] >= second('2026-11-21T01:00:00Z')]
    assert sum(row['seconds'] for row in remainder) == 3600
    assert stages['exposure']['counts']['warm'] == 7200
    assert split['warm'] + sum(row['seconds'] for row in remainder) == 7200


def test_multiple_splits_carve_disjoint_windows():
    stages = review(pack('S1,F01,IN,A1,,2026-11-21T00:00:00Z,2026-11-21T00:00:00Z\n'
                         'S2,F01,OUT,,,2026-11-21T00:30:00Z,2026-11-21T00:30:00Z,2\n'
                         'S3,F01,OUT,,,2026-11-21T01:00:00Z,2026-11-21T01:00:00Z,2\n',
                         doors='door,signal,effective\nEAST,OPEN,2026-11-21T00:00:00Z\n',
                         temperatures=WARM))
    assert [row['seconds'] for row in stages['capacity']['splits']] == [1800, 1800]
    assert stages['capacity']['split_totals']['duplicated'] == 0
    assert stages['capacity']['explained']


# --- 重跑与迟到 --------------------------------------------------------------

def test_late_split_is_replayed_at_effective_time():
    on_time = review(pack('S1,F01,IN,A1,,2026-11-21T00:10:00Z,2026-11-21T00:10:00Z\n'
                          'S2,F01,OUT,,,2026-11-21T00:30:00Z,2026-11-21T00:30:00Z,2\n'))
    late = review(pack('S1,F01,IN,A1,,2026-11-21T00:10:00Z,2026-11-21T00:10:00Z\n'
                       'S2,F01,OUT,,,2026-11-21T00:30:00Z,2026-11-21T00:40:00Z,2\n'
                       'S3,F01,MOVE,B1,,2026-11-21T00:50:00Z,2026-11-21T00:50:00Z\n'))
    # 生效 00:30 早于 00:50 的调位，收件 00:40 仍不晚于调位原件的收件 00:50，
    # 因此拆批单本身不算迟到，但顺序仍按生效时刻回放
    assert late['custody']['splits'][0]['late'] is False
    assert late['custody']['splits'][0]['time'] == second('2026-11-21T00:30:00Z')
    assert late['custody']['splits'][0]['late'] is False
    assert late['custody']['states']['F01'] == dict(slot='B1', ticket=None, remaining=3)
    assert late['custody']['counts']['late'] == 0
    assert on_time['custody']['states']['F01']['remaining'] == late['custody']['states']['F01']['remaining']


def test_rerunning_same_split_does_not_deduct_twice():
    moves = ('S1,F01,IN,A1,,2026-11-21T00:10:00Z,2026-11-21T00:10:00Z\n'
             'S2,F01,OUT,,,2026-11-21T00:30:00Z,2026-11-21T00:30:00Z,2\n')
    first, second = review(pack(moves)), review(pack(moves))
    expected = dict(slot='A1', ticket=None, remaining=3)
    assert first['custody']['states'] == second['custody']['states'] == {'F01': expected}
    assert first['capacity']['counts'] == second['capacity']['counts']
    assert second['custody']['counts']['released_pieces'] == 2


def test_duplicate_split_packet_is_dropped_not_deducted_twice():
    stages = review(pack('S1,F01,IN,A1,,2026-11-21T00:10:00Z,2026-11-21T00:10:00Z\n'
                         'S2,F01,OUT,,,2026-11-21T00:30:00Z,2026-11-21T00:30:00Z,2\n'
                         'S2,F01,OUT,,,2026-11-21T00:30:00Z,2026-11-21T00:31:00Z,2\n'))
    assert stages['custody']['states']['F01']['remaining'] == 3
    assert stages['custody']['counts']['released_pieces'] == 2
    assert [row['line'] for row in stages['intake']['copies']] == [4]


def test_conflicting_split_quantities_isolate_whole_event():
    stages = review(pack('S1,F01,IN,A1,,2026-11-21T00:10:00Z,2026-11-21T00:10:00Z\n'
                         'S2,F01,OUT,,,2026-11-21T00:30:00Z,2026-11-21T00:30:00Z,2\n'
                         'S2,F01,OUT,,,2026-11-21T00:30:00Z,2026-11-21T00:31:00Z,3\n'))
    assert [row['code'] for row in stages['intake']['isolated']] == ['EVENT_CONFLICT', 'EVENT_CONFLICT']
    # 冲突整组隔离后，两件拆批单都不采信，五件原样留库
    assert stages['custody']['states']['F01'] == dict(slot='A1', ticket=None)


def test_split_codes_are_registered():
    for code in ('SPLIT_INVALID', 'SPLIT_EXCEEDED'):
        assert code in CODES


# --- 归档与证据 --------------------------------------------------------------

def test_archived_split_roundtrips_and_certifies(client):
    payload = pack('S1,F01,IN,A1,,2026-11-21T00:10:00Z,2026-11-21T00:10:00Z\n'
                   'S2,F01,HOLD,,H09,2026-11-21T00:20:00Z,2026-11-21T00:20:00Z\n'
                   'S3,F01,OUT,B1,,2026-11-21T00:40:00Z,2026-11-21T00:40:00Z,2\n')
    stamp = client.post('/api/receipts', json=payload).json
    assert stamp['splits'] == dict(splits=1, shipped=2, remaining=3, attended=1800,
                                   unattributed=0, duplicated=0)
    assert stamp['pieces']['difference'] == 0
    detail = client.get(f"/api/receipts/{stamp['id']}").json
    assert detail['manifest']['id'] == stamp['id']
    export = client.get(f"/api/certificate/{stamp['id']}/export").json
    assert export['status'] == 'reconciled'
    split, = export['stages']['custody']['splits']
    assert (split['shipped'], split['remaining'], split['destination']) == (2, 3, 'B1')
    assert export['stages']['capacity']['splits'][0]['warm'] >= 0


def test_refresh_split_receipt_is_idempotent(client):
    payload = pack('S1,F01,IN,A1,,2026-11-21T00:10:00Z,2026-11-21T00:10:00Z\n'
                   'S2,F01,OUT,,,2026-11-21T00:30:00Z,2026-11-21T00:30:00Z,2\n')
    first = client.post('/api/receipts', json=payload).json
    again = client.post(f"/api/receipts/{first['id']}/refresh").json
    assert again['reused'] and again['manifest'] == first['manifest']
    assert again['splits']['shipped'] == 2 and again['pieces']['in_stock'] == 3


def test_capacity_page_lists_split_ledger(client):
    payload = pack('S1,F01,IN,A1,,2026-11-21T00:10:00Z,2026-11-21T00:10:00Z\n'
                   'S2,F01,OUT,B1,,2026-11-21T00:30:00Z,2026-11-21T00:30:00Z,2\n')
    stamp = client.post('/api/receipts', json=payload).json
    html = client.get(f"/view/capacity?receipt={stamp['id']}").get_data(as_text=True)
    assert '拆批台账' in html and '结清 2 件' in html and 'B1' in html


def test_split_kind_alias_and_invalid_quantity():
    # kind=SPLIT 与 OUT+pieces 等价；件数非法时整条隔离，不按整批悄悄出库。
    stages = review(pack('S1,F01,IN,A1,,2026-11-21T00:10:00Z,2026-11-21T00:10:00Z\n'
                         'S2,F01,SPLIT,,,2026-11-21T00:30:00Z,2026-11-21T00:30:00Z,2\n'))
    assert stages['custody']['states']['F01'] == dict(slot='A1', ticket=None, remaining=3)
    bad = review(pack('S1,F01,IN,A1,,2026-11-21T00:10:00Z,2026-11-21T00:10:00Z\n'
                      'S2,F01,OUT,,,2026-11-21T00:30:00Z,2026-11-21T00:30:00Z,abc\n'))
    assert [(row['event'], row['code']) for row in bad['intake']['isolated']] == [('S2', 'SPLIT_INVALID')]
    # 隔离后状态保持五件整票，没有被误当整批出库清掉
    assert bad['custody']['states']['F01'] == dict(slot='A1', ticket=None)


def test_remainder_after_split_moves_and_keeps_inspection():
    stages = review(pack('S1,F01,IN,A1,,2026-11-21T00:10:00Z,2026-11-21T00:10:00Z\n'
                         'S2,F01,HOLD,,H09,2026-11-21T00:20:00Z,2026-11-21T00:20:00Z\n'
                         'S3,F01,OUT,,,2026-11-21T00:30:00Z,2026-11-21T00:30:00Z,2\n'
                         'S4,F01,MOVE,B1,,2026-11-21T00:40:00Z,2026-11-21T00:40:00Z\n'))
    # 拆后三件余件可整批调位，查验单随调位带走
    assert stages['custody']['states']['F01'] == dict(slot='B1', ticket='H09', remaining=3)
    assert stages['capacity']['counts']['frozen'] == 3
    assert stages['capacity']['counts']['unplaced'] == 0
