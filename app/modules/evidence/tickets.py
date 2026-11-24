"""Issued station evidence tickets (收件凭证).

A ticket is bound to one archive run and one destination.  Issuing is
idempotent on that pair: retrying the original issuance returns the same
ticket, so a receipt permission never multiplies into several usable links.
Revocation is sticky in the same row, which means every URL handed out before
the withdrawal stops downloading and a later retry cannot mint a fresh one.
"""
from contextlib import closing
from datetime import datetime, timezone
from secrets import token_urlsafe
import sqlite3

from app.errors import DeskError
from app.manifest import fingerprint


def _now():
    return datetime.now(timezone.utc).isoformat()


class Tickets:
    def __init__(self, path):
        self.path = path
        with closing(self.connect()) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS evidence_tickets ('
                       'id TEXT PRIMARY KEY, run TEXT NOT NULL, destination TEXT NOT NULL, '
                       'token TEXT NOT NULL UNIQUE, payload_sha256 TEXT NOT NULL, '
                       'issued_at TEXT NOT NULL, revoked_at TEXT)')
            db.execute('CREATE INDEX IF NOT EXISTS evidence_tickets_run ON evidence_tickets (run)')

    def connect(self):
        return sqlite3.connect(self.path, timeout=15)

    @staticmethod
    def key(run, destination):
        return fingerprint(['evidence-ticket/1', run, destination])

    def issue(self, run, destination, payload_sha256):
        key = self.key(run, destination)
        with closing(self.connect()) as db, db:
            # Idempotent on (run, station): a retried issuance returns the very
            # same ticket, its token and — after a withdrawal — its revoked
            # state.  No second usable link is ever minted for the same pair.
            db.execute('INSERT OR IGNORE INTO evidence_tickets VALUES (?, ?, ?, ?, ?, ?, NULL)',
                       (key, run, destination, token_urlsafe(24), payload_sha256, _now()))
        return self.get(key)

    def get(self, key):
        with closing(self.connect()) as db:
            db.row_factory = sqlite3.Row
            row = db.execute('SELECT * FROM evidence_tickets WHERE id=?', (key,)).fetchone()
        if row is None:
            raise DeskError('NO_TICKET', '证据签发不存在', 404)
        return self._view(dict(row))

    def resolve(self, identifier):
        """Look a ticket up by management id or by the token embedded in a link."""
        with closing(self.connect()) as db:
            db.row_factory = sqlite3.Row
            row = db.execute('SELECT * FROM evidence_tickets WHERE id=? OR token=?',
                             (identifier, identifier)).fetchone()
        if row is None:
            raise DeskError('NO_TICKET', '证据签发不存在', 404)
        return self._view(dict(row))

    def revoke(self, identifier):
        with closing(self.connect()) as db, db:
            row = db.execute('SELECT id FROM evidence_tickets WHERE id=? OR token=?',
                             (identifier, identifier)).fetchone()
            if row is None:
                raise DeskError('NO_TICKET', '证据签发不存在', 404)
            db.execute('UPDATE evidence_tickets SET revoked_at=? WHERE id=? AND revoked_at IS NULL',
                       (_now(), row[0]))
        return self.get(row[0])

    def revoke_where(self, run, destination):
        with closing(self.connect()) as db, db:
            db.execute('UPDATE evidence_tickets SET revoked_at=? '
                       'WHERE run=? AND destination=? AND revoked_at IS NULL',
                       (_now(), run, destination))
        return [ticket for ticket in self.list(run)
                if ticket['destination'] == destination and ticket['revoked_at'] is not None]

    def list(self, run=None):
        with closing(self.connect()) as db:
            db.row_factory = sqlite3.Row
            if run is None:
                rows = db.execute('SELECT * FROM evidence_tickets ORDER BY rowid DESC').fetchall()
            else:
                rows = db.execute('SELECT * FROM evidence_tickets WHERE run=? ORDER BY rowid DESC',
                                  (run,)).fetchall()
        return [self._view(dict(row)) for row in rows]

    @staticmethod
    def _view(row):
        return dict(id=row['id'], run=row['run'], destination=row['destination'], token=row['token'],
                    payload_sha256=row['payload_sha256'], issued_at=row['issued_at'],
                    revoked_at=row['revoked_at'], usable=row['revoked_at'] is None)
