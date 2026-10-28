"""Portable staging names; source drives never become Linux absolute paths."""
import hashlib
import re
from pathlib import PureWindowsPath

def portable_name(source):
    name = PureWindowsPath(str(source)).name
    name = re.sub(r'[^A-Za-z0-9_.-]', '_', name)
    return 'assets/' + hashlib.sha256(str(source).encode()).hexdigest()[:24] + '/' + name

def reject_expression(path):
    if any(x in path for x in ('$', '`', '<F', '%', 'op:', 'opdef:', 'http:', 'https:', 'asset:', '[')):
        raise ValueError('Unresolved or unsupported asset expression: ' + path)
