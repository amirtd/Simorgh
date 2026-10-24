"""Run using Houdini 22 hython after sourcing houdini_setup.
Requires an explicitly trusted fixture; writes only a newly created output directory.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

p = argparse.ArgumentParser()
p.add_argument('--output', required=True)
p.add_argument('--engine', choices=['cpu', 'xpu'], default='xpu')
p.add_argument('--gpu', default='0')
p.add_argument('--start', type=int, default=1)
p.add_argument('--end', type=int, default=3)
a = p.parse_args()
import hou
from pxr import Usd, UsdRender
if hou.applicationVersion()[0] != 22 or 'apprentice' in str(hou.licenseCategory()).lower():
    raise SystemExit('Requires licensed Houdini 22 commercial/Indie; Apprentice unsupported')
out = Path(a.output).resolve()
out.mkdir(parents=True, exist_ok=False)
scene = Path(__file__).with_name('glass.usda')
stage = Usd.Stage.Open(str(scene))
if not stage or not stage.GetPrimAtPath('/World/glass/surface'):
    raise SystemExit('Fixture failed USD validation')
env = os.environ.copy()
env['CUDA_VISIBLE_DEVICES'] = a.gpu
if a.engine == 'xpu':
    env['KARMA_XPU_DISABLE_EMBREE_DEVICE'] = '1'
results = []
for frame in range(a.start, a.end + 1):
    output = out / ('glass.%04d.exr' % frame)
    began = time.monotonic()
    proc = subprocess.run([str(Path(os.environ['HFS']) / 'bin/husk'), '-R', 'BRAY_HdKarmaXPU' if a.engine == 'xpu' else 'BRAY_HdKarma', '--engine', a.engine, '--allowed-procedurals', 'none', '-V', '4', '-f', str(frame), '-n', '1', '--res', '128', '128', '-o', str(output), str(scene)], env=env, capture_output=True, text=True)
    log = proc.stdout + '\n' + proc.stderr
    (out / ('frame.%04d.log' % frame)).write_text(log)
    ok = proc.returncode == 0 and output.exists() and output.stat().st_size > 0
    # Return success separately from device evidence; logs vary by build.
    gpu_evidence = bool(re.search(r'(OptiX|CUDA).*device|device.*(OptiX|CUDA|NVIDIA)', log, re.I))
    results.append({'frame': frame, 'render_succeeded': ok, 'gpu_device_log_evidence': gpu_evidence, 'seconds': time.monotonic() - began})
report = {'houdini': hou.applicationVersionString(), 'license': str(hou.licenseCategory()), 'engine': a.engine, 'gpu_selection': a.gpu, 'frames': results}
(out / 'verification.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
if not results or not all(x['render_succeeded'] for x in results):
    raise SystemExit(1)
if a.engine == 'xpu' and not all(x['gpu_device_log_evidence'] for x in results):
    raise SystemExit('Frames exist but GPU device evidence was not found; inspect logs before accepting GPU verification')
