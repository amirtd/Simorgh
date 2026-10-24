import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid

BASE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(BASE), str(BASE / 'linux')]
from shared.job_schema import validate, digest, inside
from shared.path_mapping import portable_name, reject_expression
import render_queue as q
import render_job as r
from windows.submit_render import Client
from diagnose import detect


def fixture(root, frames=(1,)):
    jid = uuid.uuid4().hex
    bundle = root / 'scenes' / jid
    bundle.mkdir(parents=True)
    scene = bundle / 'scene.usdc'
    scene.write_text('test fixture, not a real USD')
    spec = dict(version=1, id=jid, renderer='xpu', start=frames[0], end=frames[-1], step=1, width=128, height=128, format='exr', frames={str(f): scene.name for f in frames}, files={scene.name: digest(scene)}, trusted=True)
    (bundle / 'job.json').write_text(json.dumps(spec))
    return spec

class Core(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.patches = [patch.object(q, 'ROOT', self.root), patch.object(r, 'ROOT', self.root)]
        for p in self.patches:
            p.start()
        for name in ('logs', 'outputs', 'jobs'):
            (self.root / name).mkdir()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def test_validation_injection_and_traversal(self):
        s = fixture(self.root)
        s['renderer'] = 'xpu; touch /tmp/pwn'
        with self.assertRaises(ValueError):
            validate(s)
        with self.assertRaises(ValueError):
            inside(self.root, '../escape')
        (self.root / 'link').symlink_to('/tmp')
        with self.assertRaises(ValueError):
            inside(self.root, 'link/escape')

    def test_windows_paths(self):
        p = portable_name(r'D:\Phoenix\textures\glass.exr')
        self.assertTrue(p.startswith('assets/'))
        self.assertNotIn(':', p)
        self.assertNotIn('\\', p)
        for value in ('$HIP/a.exr', 'a.$F4.vdb', 'op:/obj/foo'):
            with self.assertRaises(ValueError):
                reject_expression(value)

    def test_missing_asset_and_checksum(self):
        s = fixture(self.root)
        (self.root / 'scenes' / s['id'] / 'scene.usdc').unlink()
        with self.assertRaisesRegex(ValueError, 'Missing'):
            q.dispatch({'action': 'submit', 'id': s['id']})

    def test_queue_persistence_and_cancel(self):
        s = fixture(self.root)
        q.dispatch({'action': 'submit', 'id': s['id']})
        db = q.connect()
        db.close()
        db = q.connect()
        self.assertEqual(db.execute('SELECT state FROM jobs').fetchone()[0], 'queued')
        q.dispatch({'action': 'cancel', 'id': s['id']})
        self.assertEqual(db.execute('SELECT cancel FROM jobs').fetchone()[0], 1)
        self.assertEqual(q.dispatch({'action': 'status', 'id': s['id']})['status'], 'queued')
        with self.assertRaises(ValueError):
            q.dispatch({'action': 'submit', 'id': s['id']})

    def mock_render(self, frames):
        s = fixture(self.root, frames)
        q.dispatch({'action': 'submit', 'id': s['id']})
        hfs = self.root / 'hfs'
        (hfs / 'bin').mkdir(parents=True)
        fake = hfs / 'bin/husk'
        fake.write_text('#!/usr/bin/env python3\nimport sys\nfrom pathlib import Path\nPath(sys.argv[sys.argv.index("-o")+1]).write_bytes(b"fake rendered frame")\n')
        fake.chmod(0o700)
        (self.root / 'server.json').write_text(json.dumps({'hfs': str(hfs), 'gpu': '0'}))
        with patch.object(r, 'gpu_metrics', return_value=[]):
            state = r.run(s['id'], lambda: False)
        self.assertEqual(state, 'completed')
        manifest = json.loads((self.root / 'outputs' / s['id'] / 'manifest.json').read_text())
        self.assertEqual(len(manifest), len(frames))
        return s, manifest

    def test_single_frame_mock_renderer(self):
        self.mock_render((1,))

    def test_sequence_mock_renderer(self):
        self.mock_render((1, 2, 3))

    def test_process_group_cancellation(self):
        process = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(60)'], start_new_session=True)
        r.stop(process)
        self.assertIsNotNone(process.poll())

    def test_resume_download_and_no_overwrite(self):
        s, manifest = self.mock_render((1, 2))
        source = self.root / 'outputs' / s['id']
        destination = self.root / 'download'
        destination.mkdir()
        first = next(iter(manifest))
        (destination / (first + '.part')).write_bytes((source / first).read_bytes()[:5])
        class SFTP:
            def open(self, remote, mode):
                return (source / Path(remote).name).open(mode)
        client = Client.__new__(Client)
        client.sftp, client.remote = SFTP(), '/remote'
        client.rpc = lambda action, jid: manifest
        client.download(s['id'], destination)
        client.download(s['id'], destination)
        self.assertEqual(digest(destination / first), manifest[first]['sha256'])
        (destination / first).write_bytes(b'user data')
        with self.assertRaises(FileExistsError):
            client.download(s['id'], destination)

    def test_worker_cancels_and_continues_queue(self):
        import time
        first = fixture(self.root, (1,))
        second = fixture(self.root, (2,))
        for spec in (first, second):
            q.dispatch({'action': 'submit', 'id': spec['id']})
        hfs = self.root / 'hfs'
        (hfs / 'bin').mkdir(parents=True)
        fake = hfs / 'bin/husk'
        fake.write_text('#!/usr/bin/env python3\nimport sys,time\nfrom pathlib import Path\nif sys.argv[sys.argv.index("-f")+1] == "1": time.sleep(30)\nPath(sys.argv[sys.argv.index("-o")+1]).write_bytes(b"fake frame")\n')
        fake.chmod(0o700)
        (self.root / 'server.json').write_text(json.dumps({'hfs': str(hfs), 'gpu': '0'}))
        env = dict(os.environ, HRR_ROOT=str(self.root))
        worker = subprocess.Popen([sys.executable, str(BASE / 'linux/render_worker.py')], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        def wait_state(jid, state):
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                result = q.dispatch({'action': 'status', 'id': jid})
                if result['status'] == state:
                    return result
                if worker.poll() is not None:
                    self.fail('Worker exited: ' + worker.stderr.read().decode())
                time.sleep(0.1)
            self.fail('Timeout: ' + str(result))
        try:
            wait_state(first['id'], 'running')
            q.dispatch({'action': 'cancel', 'id': first['id']})
            wait_state(first['id'], 'cancelled')
            result = wait_state(second['id'], 'completed')
            self.assertEqual(result['completed_frames'], [2])
        finally:
            worker.terminate()
            try:
                worker.communicate(timeout=15)
            except subprocess.TimeoutExpired:
                worker.kill()
                worker.communicate()

    def test_gpu_detection_mock(self):
        with patch.object(r.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '0, GPU-123, RTX 5060 Ti, 10, 20, 16000\n')):
            self.assertEqual(r.gpu_metrics()[0]['name'], 'RTX 5060 Ti')

    def test_houdini_detection(self):
        with patch('diagnose.probe', return_value={'returncode': 0}), patch('diagnose.glob.glob', return_value=[]), patch('diagnose.shutil.which', return_value=None), patch.dict(os.environ, {'HFS': ''}):
            self.assertIsNone(detect()['hfs'])

    def test_ssh_wire_protocol(self):
        self.assertEqual(q.dispatch({'action': 'ping'}), {'ok': True, 'protocol': 1})

class Live(unittest.TestCase):
    @unittest.skipUnless(os.getenv('HRR_LIVE_CONFIG'), 'Requires deployed server and explicit SSH config')
    def test_ssh_transfer_render_download(self):
        cfg = json.loads(Path(os.environ['HRR_LIVE_CONFIG']).read_text())
        client = Client(cfg)
        try:
            self.assertTrue(client.rpc('ping')['ok'])
            # Run with a real Houdini-exported, trusted bundle.
            bundle = Path(os.environ['HRR_LIVE_BUNDLE'])
            jid = client.upload(bundle)['id']
            import time
            deadline = time.monotonic() + 600
            while time.monotonic() < deadline:
                state = client.rpc('status', jid)
                if state['status'] in ('completed', 'failed', 'cancelled'):
                    break
                time.sleep(2)
            self.assertEqual(state['status'], 'completed', state)
            with tempfile.TemporaryDirectory() as out:
                self.assertGreater(client.download(jid, out)['downloaded'], 0)
        finally:
            client.close()

if __name__ == '__main__':
    unittest.main()
