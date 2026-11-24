import pytest
from app.main import build
from app.parcels import load_example
from app.pipeline import review


@pytest.fixture
def dirty():
    return review(load_example('dirty'))


@pytest.fixture
def client(tmp_path):
    return build(tmp_path/'dock.sqlite3').test_client()


@pytest.fixture
def archived(client):
    return client.post('/api/receipts', json={'sample':'dirty'}).json
