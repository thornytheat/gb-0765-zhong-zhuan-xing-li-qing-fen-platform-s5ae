from contextlib import closing
import json
from pathlib import Path
import sqlite3

from app.errors import DeskError
from app.manifest import canonical


class Archive:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, inputs TEXT NOT NULL, result TEXT NOT NULL)')

    def connect(self):
        return sqlite3.connect(self.path, timeout=15)

    def commit(self, key, files, result):
        with closing(self.connect()) as db, db:
            cursor = db.execute('INSERT OR IGNORE INTO runs VALUES (?, ?, ?)', (key, canonical(files), canonical(result)))
            stored = db.execute('SELECT result FROM runs WHERE id=?', (key,)).fetchone()[0]
        return json.loads(stored), cursor.rowcount == 0

    def get(self, key):
        with closing(self.connect()) as db:
            row = db.execute('SELECT inputs, result FROM runs WHERE id=?', (key,)).fetchone()
        if row is None:
            raise DeskError('NO_RUN', '归档不存在', 404)
        return json.loads(row[0]), json.loads(row[1])

    def list(self):
        with closing(self.connect()) as db:
            rows = db.execute('SELECT result FROM runs ORDER BY rowid DESC').fetchall()
        return [json.loads(row[0])['manifest'] for row in rows]
