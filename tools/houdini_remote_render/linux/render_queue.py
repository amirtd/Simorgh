"""Fixed SSH entry point; persistent SQLite queue and JSON snapshots."""
import json
import os
from pathlib import Path
import sqlite3
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared.job_schema import validate, job_id, inside, digest, atomic_json

ROOT = Path(os.environ.get('HRR_ROOT', str(Path.home() / 'houdini-render'))).resolve()

def connect():
    ROOT.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(ROOT / 'queue.sqlite', timeout=30)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, state TEXT, created REAL, cancel INTEGER DEFAULT 0)')
    db.commit()
    return db

def status_path(jid):
    return ROOT / 'jobs' / job_id(jid) / 'status.json'

def snapshot(jid, **changes):
    path = status_path(jid)
    old = json.loads(path.read_text()) if path.exists() else {'id': jid, 'completed_frames': [], 'current_frame': None, 'percentage': 0, 'eta_seconds': None, 'gpu': [], 'errors': [], 'frame_seconds': {}}
    old.update(changes, updated=time.time())
    atomic_json(path, old)
    return old

def dispatch(req):
    action = req['action']
    if action == 'ping':
        return {'ok': True, 'protocol': 1}
    jid = job_id(req['id'])
    db = connect()
    if action == 'submit':
        bundle = ROOT / 'scenes' / jid
        spec = json.loads((bundle / 'job.json').read_text())
        frames = validate(spec)
        if spec['id'] != jid:
            raise ValueError('Job ID mismatch')
        for name, sha in spec['files'].items():
            path = inside(bundle, name)
            if not path.is_file() or digest(path) != sha:
                raise ValueError('Missing or corrupt asset: ' + name)
        # Snapshot must exist before the worker can claim the row.
        with db:
            if db.execute('SELECT 1 FROM jobs WHERE id=?', (jid,)).fetchone():
                raise ValueError('Job already submitted')
            (ROOT / 'jobs' / jid).mkdir(parents=True, exist_ok=True)
            snapshot(jid, status='queued', total_frames=len(frames))
            db.execute('INSERT INTO jobs(id,state,created) VALUES(?,?,?)', (jid, 'queued', time.time()))
        return {'id': jid, 'status': 'queued'}
    row = db.execute('SELECT * FROM jobs WHERE id=?', (jid,)).fetchone()
    if row is None:
        raise ValueError('Unknown job')
    if action == 'cancel':
        with db:
            db.execute('UPDATE jobs SET cancel=1 WHERE id=?', (jid,))
        return {'id': jid, 'cancellation_requested': True}
    if action == 'status':
        return json.loads(status_path(jid).read_text())
    if action == 'results':
        if row['state'] != 'completed':
            raise ValueError('Job has not completed')
        return json.loads((ROOT / 'outputs' / jid / 'manifest.json').read_text())
    raise ValueError('Unknown action')

if __name__ == '__main__':
    try:
        raw = sys.stdin.buffer.read(65537)
        if len(raw) > 65536:
            raise ValueError('Request too large')
        print(json.dumps({'ok': True, 'result': dispatch(json.loads(raw))}))
    except Exception as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}))
        sys.exit(1)
