import pytest
from app.faults import DockFault
from app.modules.certificate.service import issue


def test_attachment(client,archived):
    response = client.get(f"/api/certificate/{archived['id']}/export")
    assert 'attachment;' in response.headers['Content-Disposition']
    assert response.json['files']['moves'].startswith('\ufeffevent')


def test_certificate_preserves_absent_slot_evidence(client,archived):
    payload = client.get(f"/api/certificate/{archived['id']}/export").json
    assert payload['status']=='reconciled' and payload['stages']['exposure']['counts']['missing_slot']==900


def test_original_hash_mismatch(client,archived):
    document = client.application.extensions['ice_receipts'].read(archived['id'])
    document['files']['slots'] += '\n'
    with pytest.raises(DockFault, match='散列'):
        issue(document)


def test_result_hash_mismatch(client,archived):
    document = client.application.extensions['ice_receipts'].read(archived['id'])
    document['stages']['capacity']['counts']['free'] = 127
    with pytest.raises(DockFault, match='散列'):
        issue(document)


def test_stamp_manifest(client,archived):
    assert client.get(f"/api/certificate/{archived['id']}").json['manifest'] == archived['manifest']


def test_failed_certificate(client):
    assert client.get('/api/certificate/unknown/export').status_code == 404
