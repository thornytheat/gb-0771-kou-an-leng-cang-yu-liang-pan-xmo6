from flask import Blueprint, current_app, jsonify, request
from app.parcels import receive_pack
from .service import brief, save

history = Blueprint('history', __name__, url_prefix='/api/receipts')


def receipts():
    return current_app.extensions['ice_receipts']


@history.get('')
def listing():
    rows = receipts().list()
    return jsonify(rows=rows, count=len(rows))


@history.post('')
def publish():
    return jsonify(save(receipts(), receive_pack(request.get_json(silent=True))))


@history.get('/<key>')
def detail(key):
    return jsonify(brief(receipts().read(key)))


@history.post('/<key>/refresh')
def refresh(key):
    return jsonify(save(receipts(), receipts().read(key)['files']))
