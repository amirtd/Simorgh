"""Houdini-side Solaris exporter and SSH/SFTP client. Requires paramiko."""
import glob
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import uuid
import xml.etree.ElementTree as ET
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared.job_schema import validate, relative, digest, atomic_json
from shared.path_mapping import reject_expression

CONFIG = Path.home() / '.houdini-remote-render' / 'connection.json'

def load_config():
    return json.loads(CONFIG.read_text()) if CONFIG.exists() else {}

def save_config(cfg):
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    atomic_json(CONFIG, cfg)

class Bundle:
    def __init__(self, root):
        self.root = Path(root)
        self.done = {}

    def add(self, source):
        from pxr import Sdf, UsdUtils
        source = str(Path(source).resolve())
        if source in self.done:
            return self.done[source]
        reject_expression(source.replace('<UDIM>', 'UDIM'))
        p = Path(source)
        # Keep files in a source directory together (UDIMs and XML relatives).
        target = 'assets/' + hashlib.sha256(str(p.parent).encode()).hexdigest()[:24] + '/' + p.name
        relative(target)
        if not p.is_file():
            raise ValueError('Missing asset: ' + source)
        self.done[source] = target
        dest = self.root / target
        dest.parent.mkdir(parents=True, exist_ok=True)
        if p.suffix.lower() in ('.usd', '.usda', '.usdc'):
            layer = Sdf.Layer.FindOrOpen(source)
            if not layer:
                raise ValueError('Cannot read USD: ' + source)
            copy = Sdf.Layer.CreateAnonymous('.usda')
            copy.TransferContent(layer)
            UsdUtils.ModifyAssetPaths(copy, lambda value: self.remap(value, layer, dest))
            if not copy.Export(str(dest)):
                raise RuntimeError('USD export failed')
        elif p.suffix.lower() == '.mtlx':
            tree = ET.parse(p)
            for node in tree.iter():
                for key in ('file', 'href'):
                    if node.get(key):
                        node.set(key, self.xml_asset(node.get(key), p, dest))
                if node.get('type') == 'filename' and node.get('value'):
                    node.set('value', self.xml_asset(node.get('value'), p, dest))
            tree.write(dest, encoding='utf-8', xml_declaration=True)
        else:
            shutil.copyfile(p, dest)
        return target

    def xml_asset(self, value, source, dest):
        reject_expression(value.replace('<UDIM>', 'UDIM'))
        return self.copy_pattern(str(source.parent / value), dest)

    def copy_pattern(self, source, dest):
        if '<UDIM>' in source:
            matches = glob.glob(source.replace('<UDIM>', '[0-9][0-9][0-9][0-9]'))
            if not matches:
                raise ValueError('Missing UDIM tiles: ' + source)
            targets = [self.add(x) for x in matches]
            pattern = str(Path(targets[0]).parent / Path(source).name)
            return os.path.relpath(self.root / pattern, dest.parent).replace('\\', '/')
        target = self.add(source)
        return os.path.relpath(self.root / target, dest.parent).replace('\\', '/')

    def remap(self, value, layer, dest):
        from pxr import Sdf, Ar
        if not value:
            return value
        reject_expression(value.replace('<UDIM>', 'UDIM'))
        source = Sdf.ComputeAssetPathRelativeToLayer(layer, value)
        if '<UDIM>' not in source:
            resolved = str(Ar.GetResolver().Resolve(source))
            if not resolved:
                raise ValueError('Unresolved USD asset: ' + value)
            source = resolved
        return self.copy_pattern(source, dest)

def export_bundle(settings, destination):
    import hou
    from pxr import Sdf, UsdUtils, UsdRender
    if hou.applicationVersion()[0] != 22:
        raise ValueError('This pipeline requires Houdini 22')
    if not settings.get('trusted'):
        raise ValueError('Explicit trust acknowledgment is required')
    if 'apprentice' in str(hou.licenseCategory()).lower() or hou.hipFile.path().lower().endswith('.hipnc'):
        raise ValueError('Apprentice/non-commercial export is unsupported; no license conversion is attempted')
    node = hou.node(settings['lop'])
    if node is None or node.type().category() != hou.lopNodeTypeCategory():
        raise ValueError('Select a Solaris LOP node with camera and Render Settings')
    hou.hipFile.save()
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=False)
    jid = uuid.uuid4().hex
    spec = dict(version=1, id=jid, renderer=settings['renderer'], start=settings['start'], end=settings['end'], step=settings['step'], width=settings['width'], height=settings['height'], format=settings['format'], frames={}, files={}, trusted=True)
    original_frame = hou.frame()
    bundle = Bundle(root)
    try:
        for frame in range(spec['start'], spec['end'] + 1, spec['step']):
            hou.setFrame(frame)
            stage = node.stage()
            render_settings = [p for p in stage.Traverse() if p.IsA(UsdRender.Settings)]
            if len(render_settings) != 1:
                raise ValueError('Select a LOP stage containing exactly one USD Render Settings prim')
            products = UsdRender.Settings(render_settings[0]).GetProductsRel().GetTargets()
            if len(products) != 1:
                raise ValueError('This workflow requires exactly one render product')
            if not UsdRender.Settings(render_settings[0]).GetCameraRel().GetTargets():
                raise ValueError('Render Settings must reference a camera')
            for prim in stage.Traverse():
                if 'procedural' in prim.GetTypeName().lower() or any('procedural' in attr.GetName().lower() for attr in prim.GetAttributes()):
                    raise ValueError('Bake procedural geometry before export: ' + str(prim.GetPath()))
            layer = stage.Flatten()
            layer.pseudoRoot.SetInfo('renderSettingsPrimPath', str(render_settings[0].GetPath()))
            dest = root / ('scene.%04d.usdc' % frame)
            # Flatten resolves references; asset-valued data still needs copying.
            UsdUtils.ModifyAssetPaths(layer, lambda value: bundle.remap(value, layer, dest))
            if not layer.Export(str(dest)):
                raise RuntimeError('Failed to export cooked Solaris stage')
            layers, assets, unresolved = UsdUtils.ComputeAllDependencies(str(dest))
            if unresolved:
                raise ValueError('Missing dependencies: ' + ', '.join(map(str, unresolved)))
            spec['frames'][str(frame)] = dest.name
        spec['files'] = {p.relative_to(root).as_posix(): digest(p) for p in root.rglob('*') if p.is_file()}
        validate(spec)
        atomic_json(root / 'job.json', spec)
        return spec
    finally:
        hou.setFrame(original_frame)

class Client:
    def __init__(self, cfg):
        import paramiko
        self.cfg = cfg
        self.ssh = paramiko.SSHClient()
        self.ssh.load_system_host_keys()
        known = Path.home() / '.ssh' / 'known_hosts'
        if known.exists():
            self.ssh.load_host_keys(str(known))
        self.ssh.set_missing_host_key_policy(paramiko.RejectPolicy())
        self.ssh.connect(cfg['host'], port=int(cfg.get('port', 22)), username=cfg['username'], allow_agent=True, look_for_keys=True, timeout=15, auth_timeout=15, banner_timeout=15)
        self.sftp = self.ssh.open_sftp()
        self.home = self.sftp.normalize('.')
        self.remote = self.home + '/houdini-render'

    def close(self):
        self.sftp.close()
        self.ssh.close()

    def rpc(self, action, jid=None):
        req = {'action': action}
        if jid is not None:
            req['id'] = jid
        stdin, stdout, stderr = self.ssh.exec_command('python3 houdini-render/scripts/linux/render_queue.py', timeout=30)
        stdin.write(json.dumps(req))
        stdin.flush()
        stdin.channel.shutdown_write()
        raw = stdout.read()
        error = stderr.read().decode(errors='replace')
        if not raw:
            raise RuntimeError('Remote command failed: ' + error[-1000:])
        answer = json.loads(raw)
        if not answer['ok']:
            raise RuntimeError(answer['error'])
        return answer['result']

    def mkdirs(self, path):
        current = self.remote
        for part in relative(path).split('/'):
            current += '/' + part
            try:
                self.sftp.mkdir(current, mode=0o700)
            except OSError:
                import stat
                if not stat.S_ISDIR(self.sftp.lstat(current).st_mode):
                    raise ValueError('Remote path is not a directory')

    def upload(self, bundle):
        bundle = Path(bundle)
        spec = json.loads((bundle / 'job.json').read_text())
        validate(spec)
        # An unsubmitted UUID directory can be retried. Each upload is atomic.
        for name in list(spec['files']) + ['job.json']:
            remote = 'scenes/' + spec['id'] + '/' + relative(name)
            self.mkdirs(str(Path(remote).parent).replace('\\', '/'))
            target = self.remote + '/' + remote
            self.sftp.put(str(bundle / name), target + '.part')
            self.sftp.posix_rename(target + '.part', target)
        return self.rpc('submit', spec['id'])

    def download(self, jid, directory):
        from shared.job_schema import job_id
        job_id(jid)
        manifest = self.rpc('results', jid)
        directory = Path(directory).resolve()
        directory.mkdir(parents=True, exist_ok=True)
        for name, info in manifest.items():
            relative(name)
            if '/' in name:
                raise ValueError('Unexpected result path')
            dest = directory / name
            if dest.is_symlink():
                raise ValueError('Refusing symlink result destination')
            if dest.exists():
                if digest(dest) == info['sha256']:
                    continue
                raise FileExistsError('Refusing to overwrite existing frame: ' + str(dest))
            part = dest.with_name(dest.name + '.part')
            if part.is_symlink():
                raise ValueError('Refusing symlink partial file')
            offset = part.stat().st_size if part.exists() else 0
            if offset > info['size']:
                raise ValueError('Partial download is larger than source')
            remote = self.remote + '/outputs/' + jid + '/' + name
            with self.sftp.open(remote, 'rb') as src, part.open('ab') as dst:
                src.seek(offset)
                shutil.copyfileobj(src, dst, 1024 * 1024)
            if part.stat().st_size != info['size'] or digest(part) != info['sha256']:
                raise ValueError('Checksum mismatch; remove partial file and retry: ' + str(part))
            part.rename(dest)
        return {'downloaded': len(manifest), 'directory': str(directory)}

def main():
    import argparse
    parser = argparse.ArgumentParser(description='SSH render client (export scenes using the Houdini shelf tool)')
    parser.add_argument('action', choices=['ping', 'submit', 'status', 'cancel', 'download'])
    parser.add_argument('--config', type=Path, default=CONFIG)
    parser.add_argument('--bundle', type=Path)
    parser.add_argument('--job')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.action == 'submit' and not args.bundle:
        parser.error('submit requires --bundle')
    if args.action in ('status', 'cancel', 'download') and not args.job:
        parser.error('This action requires --job')
    if args.action == 'download' and not args.output:
        parser.error('download requires --output')
    cfg = json.loads(args.config.read_text())
    client = Client(cfg)
    try:
        if args.action == 'submit':
            result = client.upload(args.bundle)
        elif args.action == 'download':
            result = client.download(args.job, args.output)
        else:
            result = client.rpc(args.action, args.job)
        print(json.dumps(result, indent=2))
    finally:
        client.close()

if __name__ == '__main__':
    main()
