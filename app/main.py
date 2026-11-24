import os
from flask import Flask, jsonify, request
from werkzeug.exceptions import RequestEntityTooLarge
from .config import VERSION
from .errors import DeskError
from .modules.archive.routes import bp as archive
from .modules.archive.store import Archive
from .modules.evidence.routes import bp as evidence
from .web import bp as desk


def create_app(path=None):
    app = Flask(__name__)
    app.select_jinja_autoescape = lambda name: name is None or name.endswith(('.html', '.jinja'))
    app.url_map.redirect_defaults = False
    app.config['MAX_CONTENT_LENGTH'] = 2_000_000
    app.extensions['transfer_archive'] = Archive(path or os.getenv('LUGGAGE_DB', 'var/transfer.sqlite3'))
    for routes in (archive, evidence, desk):
        app.register_blueprint(routes)

    @app.get('/health')
    def health():
        return jsonify(status='ok', version=VERSION)

    @app.errorhandler(DeskError)
    def business_error(error):
        if not request.path.startswith('/api/'):
            from flask import render_template
            return render_template('error.jinja', message=str(error)), error.status
        return jsonify(code=error.code, message=str(error)), error.status

    @app.errorhandler(RequestEntityTooLarge)
    def too_big(_):
        return jsonify(code='TOO_LARGE', message='原件超过 2 MB'), 413

    return app
