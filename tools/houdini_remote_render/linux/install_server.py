import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
from diagnose import detect

p = argparse.ArgumentParser()
p.add_argument('--hfs', help='Existing Houdini 22 installation root')
p.add_argument('--gpu', default='0', help='nvidia-smi GPU index or UUID')
p.add_argument('--enable-ssh', action='store_true', help='Install/enable OpenSSH with sudo; preserve existing sshd configuration')
p.add_argument('--start', action='store_true', help='Enable/start user worker service')
a = p.parse_args()
report = detect(a.hfs)
# Avoid printing full Tailscale/network or licensing details in installation logs.
print(json.dumps({k: report[k] for k in ('os', 'gpu', 'hfs', 'licensing', 'xpu_render')}, indent=2))
if not report['hfs']:
    raise SystemExit('Houdini not found. Install/licence Houdini 22 manually, source houdini_setup, and pass --hfs /opt/hfs22.0.BUILD.')
if not report.get('xpu_delegate_available'):
    raise SystemExit('Karma XPU delegate is missing/unsupported; inspect husk --list-renderers in the sourced Houdini environment.')
if report.get('hython_license', {}).get('returncode') != 0:
    raise SystemExit('hython/license check failed. Source houdini_setup and fix licensing first.')
license_text = report['hython_license']['stdout'].lower()
if 'apprentice' in license_text or '22.0' not in license_text:
    raise SystemExit('Requires Houdini 22 with a permitted commercial/Indie license; Apprentice unsupported.')
gpu = subprocess.run(['nvidia-smi', '-i', a.gpu, '--query-gpu=driver_version', '--format=csv,noheader'], capture_output=True, text=True, check=True).stdout.strip()
if int(gpu.split('.')[0]) < 580:
    raise SystemExit('Driver below SideFX Houdini 22 baseline 580; upgrade manually after reviewing requirements.')
root = Path.home() / 'houdini-render'
source = Path(__file__).resolve().parents[1]
unit = Path.home() / '.config/systemd/user/houdini-render.service'
if (root / 'scripts').exists() or (root / 'server.json').exists() or unit.exists():
    answer = input('Existing deployment found. Replace scripts/config/service (jobs and outputs retained)? [y/N] ')
    if answer.lower() != 'y':
        raise SystemExit('No changes made')
for name in ('jobs', 'scenes', 'assets', 'outputs', 'logs', 'scripts'):
    (root / name).mkdir(parents=True, exist_ok=True, mode=0o700)
os.chmod(root, 0o700)
for name in ('linux', 'shared'):
    shutil.copytree(source / name, root / 'scripts' / name, dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__'))
(root / 'server.json').write_text(json.dumps({'hfs': report['hfs'], 'gpu': a.gpu}, indent=2))
wrapper = root / 'scripts/start-worker.sh'
wrapper.write_text('#!/usr/bin/env bash\nset -euo pipefail\ncd ' + shlex.quote(report['hfs']) + '\nsource ./houdini_setup\nexec /usr/bin/python3 ' + shlex.quote(str(root / 'scripts/linux/render_worker.py')) + '\n')
wrapper.chmod(0o700)
unit.parent.mkdir(parents=True, exist_ok=True)
# %h is expanded by systemd; no shell interpolation of user input.
unit.write_text('[Unit]\nDescription=Houdini remote render queue\nAfter=network.target\n[Service]\nType=simple\nExecStart=/bin/bash %h/houdini-render/scripts/start-worker.sh\nRestart=on-failure\nRestartSec=5\nKillMode=control-group\nTimeoutStopSec=20\nUMask=0077\n[Install]\nWantedBy=default.target\n')
if a.enable_ssh:
    subprocess.run(['sudo', 'apt-get', 'install', '-y', 'openssh-server'], check=True)
    subprocess.run(['sudo', 'systemctl', 'enable', '--now', 'ssh'], check=True)
if a.start:
    subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)
    subprocess.run(['systemctl', '--user', 'enable', '--now', 'houdini-render.service'], check=True)
print('Installed. For boot without login: sudo loginctl enable-linger ' + os.environ.get('USER', '<username>'))
print('No firewall, driver, Houdini installation, or sshd authentication policy was modified. Configure key access and private-network firewall rules per README.')
