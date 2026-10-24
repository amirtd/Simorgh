import fcntl
import json
from pathlib import Path
import shutil
import signal
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from render_queue import ROOT, connect, snapshot
from render_job import run

stopping = False

def shutdown(*_):
    global stopping
    stopping = True

def main():
    for name in ('jobs', 'scenes', 'assets', 'outputs', 'logs', 'scripts'):
        (ROOT / name).mkdir(parents=True, exist_ok=True)
    lock = (ROOT / 'worker.lock').open('w')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    db = connect()
    # Interrupted jobs fail visibly; never silently duplicate a render after restart.
    for row in db.execute("SELECT id FROM jobs WHERE state='running'").fetchall():
        snapshot(row['id'], status='failed', errors=['Worker interrupted; submit a new job'])
        shutil.rmtree(ROOT / 'jobs' / row['id'] / 'tmp', ignore_errors=True)
    with db:
        db.execute("UPDATE jobs SET state='failed' WHERE state='running'")
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    while not stopping:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute("SELECT * FROM jobs WHERE state='queued' ORDER BY created LIMIT 1").fetchone()
        if row:
            db.execute("UPDATE jobs SET state='running' WHERE id=?", (row['id'],))
        db.commit()
        if not row:
            time.sleep(1)
            continue
        jid = row['id']
        def cancelled():
            return stopping or bool(db.execute('SELECT cancel FROM jobs WHERE id=?', (jid,)).fetchone()[0])
        try:
            state = run(jid, cancelled)
            snapshot(jid, status=state, eta_seconds=0 if state == 'completed' else None)
        except Exception as exc:
            state = 'failed'
            snapshot(jid, status=state, errors=[str(exc)])
        with db:
            db.execute('UPDATE jobs SET state=? WHERE id=?', (state, jid))
        # Only per-job scratch is cleaned; scenes and final outputs are retained.
        shutil.rmtree(ROOT / 'jobs' / jid / 'tmp', ignore_errors=True)

if __name__ == '__main__':
    main()
