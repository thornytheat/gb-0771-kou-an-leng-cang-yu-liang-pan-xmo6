import os
from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import RequestEntityTooLarge
from .faults import DockFault
from .modules.certificate.routes import certificate
from .modules.history.routes import history
from .modules.history.storage import Receipts
from .web import board


def build(path=None):
    service = Flask(__name__)
    service.url_map.redirect_defaults = False
    service.config['MAX_CONTENT_LENGTH'] = 2_000_000
    service.extensions['ice_receipts'] = Receipts(path or os.environ.get('ICE_STOCK_DB', 'var/receipts.sqlite3'))
    service.register_blueprint(board)
    service.register_blueprint(history)
    service.register_blueprint(certificate)

    @service.get('/health')
    def health():
        return jsonify(status='ok')

    @service.errorhandler(DockFault)
    def problem(error):
        if request.path.startswith('/api/'):
            return jsonify(code=error.code, message=str(error)), error.status
        return render_template('failure.html', message=str(error)), error.status

    @service.errorhandler(RequestEntityTooLarge)
    def size(_):
        return jsonify(code='TOO_LARGE', message='冷库原件超过 2 MB'), 413

    return service
