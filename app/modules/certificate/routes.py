from flask import Blueprint, jsonify
from app.modules.history.routes import receipts
from .service import issue

certificate = Blueprint('certificate', __name__)


@certificate.get('/api/certificate/<key>')
def stamp(key):
    proof = issue(receipts().read(key))
    return jsonify(verified=proof['verified'], manifest=proof['manifest'], status=proof['status'])


@certificate.get('/api/certificate/<key>/export')
def export(key):
    response = jsonify(issue(receipts().read(key)))
    response.headers['Content-Disposition'] = f'attachment; filename="cold-room-{key}.json"'
    return response
