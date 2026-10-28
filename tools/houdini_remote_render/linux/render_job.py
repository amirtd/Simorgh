"""One frame per process; cancellation only signals our own process group."""
import json
import os
from pathlib import Path
import signal
import subprocess
import time
from shared.job_schema import validate, inside, digest, atomic_json
from render_queue import ROOT, snapshot

def gpu_metrics():
    try:
        p = subprocess.run(['nvidia-smi', '--query-gpu=index,uuid,name,utilization.gpu,memory.used,memory.total', '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=5, check=True)
        return [dict(zip(('index', 'uuid', 'name', 'utilization_percent', 'used_mib', 'total_mib'), [x.strip() for x in line.split(',')])) for line in p.stdout.splitlines()]
    except (OSError, subprocess.SubprocessError):
        return []

def command(husk, spec, frame, scene, output):
    delegate = 'BRAY_HdKarmaXPU' if spec['renderer'] == 'xpu' else 'BRAY_HdKarma'
    return [str(husk), '-R', delegate, '--engine', spec['renderer'], '--allowed-procedurals', 'none', '--disable-delegate-products', '--disable-hydra-generative-procedurals', '-f', str(frame), '-n', '1', '--res', str(spec['width']), str(spec['height']), '-o', str(output), str(scene)]

def stop(proc):
    if proc.poll() is None:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            proc.wait()
            return
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait()

def run(jid, cancelled):
    bundle = ROOT / 'scenes' / jid
    spec = json.loads((bundle / 'job.json').read_text())
    frames = validate(spec)
    for name, sha in spec['files'].items():
        if digest(inside(bundle, name)) != sha:
            raise ValueError('Bundle modified: ' + name)
    cfg = json.loads((ROOT / 'server.json').read_text())
    husk = Path(cfg['hfs']) / 'bin' / 'husk'
    if not husk.is_file():
        raise ValueError('Houdini husk is unavailable; run diagnostics')
    out = ROOT / 'outputs' / jid
    out.mkdir(parents=True, exist_ok=True)
    temp = ROOT / 'jobs' / jid / 'tmp'
    temp.mkdir(exist_ok=True)
    env = os.environ.copy()
    env.update(HFS=cfg['hfs'], HOUDINI_TEMP_DIR=str(temp), CUDA_VISIBLE_DEVICES=cfg['gpu'])
    if spec['renderer'] == 'xpu':
        env['KARMA_XPU_DISABLE_EMBREE_DEVICE'] = '1'
    completed, timings, manifest = [], {}, {}
    snapshot(jid, status='running')
    for frame in frames:
        if cancelled():
            return 'cancelled'
        output = out / ('frame.%04d.%s' % (frame, spec['format']))
        began = time.monotonic()
        logpath = ROOT / 'logs' / (jid + '.' + str(frame) + '.log')
        with logpath.open('wb') as log:
            proc = subprocess.Popen(command(husk, spec, frame, inside(bundle, spec['frames'][str(frame)]), output), stdout=log, stderr=subprocess.STDOUT, env=env, start_new_session=True)
            try:
                while proc.poll() is None:
                    if cancelled():
                        stop(proc)
                        return 'cancelled'
                    snapshot(jid, current_frame=frame, gpu=gpu_metrics())
                    time.sleep(1)
            finally:
                stop(proc)
        if proc.returncode or not output.exists() or output.stat().st_size == 0:
            tail = logpath.read_text(errors='replace')[-8000:]
            raise RuntimeError('Frame %s failed (exit %s). %s' % (frame, proc.returncode, tail))
        completed.append(frame)
        timings[str(frame)] = round(time.monotonic() - began, 3)
        manifest[output.name] = {'sha256': digest(output), 'size': output.stat().st_size}
        snapshot(jid, completed_frames=completed, frame_seconds=timings, percentage=100 * len(completed) / len(frames), eta_seconds=sum(timings.values()) / len(completed) * (len(frames) - len(completed)))
    atomic_json(out / 'manifest.json', manifest)
    return 'completed'
