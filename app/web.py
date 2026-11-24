from flask import Blueprint, jsonify, render_template, request
from .faults import DockFault
from .labels import TABS, CODES, KINDS
from .modules.certificate.service import issue
from .modules.history.routes import receipts
from .parcels import load_example, receive_pack
from .pipeline import review
from .swimlanes import lanes, minutes
from .utc import iso

board = Blueprint('board', __name__)


def selection():
    key, example = request.args.get('receipt'), request.args.get('sample', 'dirty')
    if key:
        doc = receipts().read(key)
        return doc['stages'], doc['manifest'], example
    return review(load_example(example)), None, example


@board.get('/api/observe/<view>')
def observe(view):
    if view not in tuple(TABS)[:5]:
        raise DockFault('NO_VIEW', '未找到查验入口', 404)
    key = request.args.get('receipt')
    if key:
        return jsonify(receipts().read(key)['stages'][view])
    return jsonify(review(load_example(request.args.get('sample', 'dirty')), until=view))


@board.post('/api/observe/<view>')
def inspect_originals(view):
    if view not in tuple(TABS)[:5]:
        raise DockFault('NO_VIEW', '未找到查验入口', 404)
    return jsonify(review(receive_pack(request.get_json(silent=True)), until=view))


@board.get('/', defaults={'view':'exposure'})
@board.get('/view/<view>')
def page(view):
    if view not in TABS:
        raise DockFault('NO_VIEW', '未找到查验入口', 404)
    stages, stamp, example = selection()
    if view == 'certificate' and stamp:
        issue(receipts().read(stamp['id']))
    tracks, ticks = lanes(stages)
    return render_template('station.html', stages=stages, view=view, stamp=stamp, sample=example, tabs=TABS,
                           codes=CODES, kinds=KINDS, tracks=tracks, ticks=ticks, utc=iso, minutes=minutes,
                           entries=receipts().list() if view == 'history' else [])
