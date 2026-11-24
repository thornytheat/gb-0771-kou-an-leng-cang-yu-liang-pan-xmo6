from concurrent.futures import ThreadPoolExecutor
from app.main import build
from app.modules.history.service import save
from app.modules.history.storage import Receipts
from app.parcels import load_example


def test_refresh_idempotent(client,archived):
    again = client.post(f"/api/receipts/{archived['id']}/refresh").json
    assert again['reused'] and again['manifest'] == archived['manifest']


def test_reopening_preserves_values(tmp_path,archived):
    client = build(tmp_path/'dock.sqlite3').test_client()
    result = client.get(f"/api/receipts/{archived['id']}").json
    assert result['manifest'] == archived['manifest'] and result['exposure']['missing_slot'] == 900


def test_atomic_invalid_window(client):
    payload = dict(load_example('dirty'),window='{"from":"no","until":"no"}')
    response = client.post('/api/receipts',json=payload)
    assert (response.status_code,response.json['code']) == (422,'WINDOW')
    assert client.get('/api/receipts').json['count'] == 0


def test_concurrent(tmp_path):
    storage = Receipts(tmp_path/'dock.sqlite3')
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _:save(storage,load_example('dirty')), range(4)))
    assert sum(not item['reused'] for item in results) == len(storage.list()) == 1


def test_unknown_receipt(client):
    response = client.get('/api/receipts/unknown')
    assert (response.status_code,response.json['code']) == (404,'NO_RECEIPT')


def test_different_pack(client,archived):
    fresh = client.post('/api/receipts',json={'sample':'clean'}).json
    assert fresh['id'] != archived['id'] and client.get('/api/receipts').json['count'] == 2
