"""Read-only diagnostics; help output is never called proof of licensing."""
import argparse
import glob
import json
import os
from pathlib import Path
import shutil
import subprocess

def probe(argv, timeout=20):
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        return {'returncode': p.returncode, 'stdout': p.stdout[-12000:], 'stderr': p.stderr[-2000:]}
    except (OSError, subprocess.SubprocessError) as exc:
        return {'error': str(exc)}

def detect(hfs=None):
    candidates = [hfs, os.environ.get('HFS')]
    executable = shutil.which('hython')
    if executable:
        candidates.append(str(Path(executable).resolve().parents[1]))
    candidates += sorted(glob.glob('/opt/hfs22*') + glob.glob('/opt/houdini/hfs22*') + glob.glob(str(Path.home() / 'hfs22*')))
    candidates = [str(Path(x).resolve()) for x in candidates if x]
    valid = [x for x in candidates if all((Path(x) / 'bin' / name).is_file() for name in ('hython', 'husk'))]
    result = {'os': Path('/etc/os-release').read_text(), 'gpu': probe(['nvidia-smi', '--query-gpu=index,uuid,name,driver_version,memory.total', '--format=csv']), 'houdini_candidates': candidates, 'hfs': valid[0] if valid else None, 'ssh': probe(['systemctl', 'is-active', 'ssh']), 'tailscale': probe(['tailscale', 'status', '--json']), 'licensing': 'unverified', 'xpu_render': 'unverified'}
    if valid:
        root = Path(valid[0])
        result['husk'] = probe([str(root / 'bin/husk'), '--help'])
        result['renderers'] = probe([str(root / 'bin/husk'), '--list-renderers'])
        renderer_text = result['renderers'].get('stdout', '') + result['renderers'].get('stderr', '')
        result['xpu_delegate_available'] = any('BRAY_HdKarmaXPU' in line and 'unsupported' not in line.lower() for line in renderer_text.splitlines())
        result['hython_license'] = probe([str(root / 'bin/hython'), '-c', 'import hou,json; print(json.dumps({"version":hou.applicationVersionString(),"license":str(hou.licenseCategory())}))'])
        result['license_inventory'] = probe([str(root / 'bin/sesictrl'), 'print-license'])
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--hfs')
    parser.add_argument('--output')
    args = parser.parse_args()
    report = detect(args.hfs)
    raw = json.dumps(report, indent=2)
    if args.output:
        with open(args.output, 'x') as f:
            f.write(raw + '\n')
    print(raw)
