"""Strict wire format. No commands or absolute server paths come from clients."""
import hashlib
import json
import re
from pathlib import Path, PurePosixPath

ID = re.compile(r'^[a-f0-9]{32}$')

def job_id(value):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise ValueError('Invalid job ID')
    return value

def relative(value):
    if not isinstance(value, str) or not value or '\\' in value or ':' in value:
        raise ValueError('Expected portable relative path')
    p = PurePosixPath(value)
    if p.is_absolute() or '..' in p.parts or str(p) != value:
        raise ValueError('Unsafe path: ' + value)
    return value

def inside(root, value):
    p = (Path(root) / relative(value)).resolve()
    if not p.is_relative_to(Path(root).resolve()):
        raise ValueError('Path escapes configured root')
    return p

def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def validate(data):
    expected = {'version', 'id', 'renderer', 'start', 'end', 'step', 'width', 'height', 'format', 'frames', 'files', 'trusted'}
    if set(data) != expected or data['version'] != 1 or data['trusted'] is not True:
        raise ValueError('Invalid schema or scene not explicitly trusted')
    job_id(data['id'])
    for key, lo, hi in [('start', -100000, 100000), ('end', -100000, 100000), ('step', 1, 10000), ('width', 1, 32768), ('height', 1, 32768)]:
        if type(data[key]) is not int or not lo <= data[key] <= hi:
            raise ValueError('Invalid ' + key)
    frames = list(range(data['start'], data['end'] + 1, data['step']))
    if not frames or len(frames) > 10000:
        raise ValueError('Invalid frame count')
    if data['renderer'] not in ('cpu', 'xpu') or data['format'] not in ('exr', 'png'):
        raise ValueError('Unsupported renderer or image format')
    if set(data['frames']) != {str(x) for x in frames}:
        raise ValueError('Frame manifest mismatch')
    if not isinstance(data['files'], dict) or len(data['files']) > 100000:
        raise ValueError('Invalid files manifest')
    for path, sha in data['files'].items():
        relative(path)
        if not re.fullmatch('[a-f0-9]{64}', sha):
            raise ValueError('Invalid checksum')
    for path in data['frames'].values():
        if relative(path) not in data['files'] or not path.endswith('.usdc'):
            raise ValueError('Frame USD missing from manifest')
    return frames

def atomic_json(path, data):
    path = Path(path)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, indent=2), encoding='utf-8')
    temp.replace(path)
