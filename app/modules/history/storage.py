from contextlib import closing
import json
from pathlib import Path
import sqlite3
from app.faults import DockFault
from app.seals import compact


class Receipts:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS receipts (id TEXT PRIMARY KEY, stamp TEXT NOT NULL, raw TEXT NOT NULL, stages TEXT NOT NULL)')

    def connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def read(self, key):
        with closing(self.connect()) as db:
            row = db.execute('SELECT stamp,raw,stages FROM receipts WHERE id=?', (key,)).fetchone()
        if row is None:
            raise DockFault('NO_RECEIPT', '冷库档案不存在', 404)
        return dict(zip(('manifest','files','stages'), map(json.loads, row)))

    def insert(self, key, stamp, files, stages):
        with closing(self.connect()) as db, db:
            cursor = db.execute('INSERT OR IGNORE INTO receipts VALUES (?,?,?,?)',
                                (key, compact(stamp), compact(files), compact(stages)))
            inserted = cursor.rowcount == 1
        return self.read(key), not inserted

    def list(self):
        with closing(self.connect()) as db:
            return [json.loads(row[0]) for row in db.execute('SELECT stamp FROM receipts ORDER BY rowid DESC')]
