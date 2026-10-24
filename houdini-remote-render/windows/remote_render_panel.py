"""Shelf entry: import remote_render_panel; remote_render_panel.show()"""
import json
from pathlib import Path
import tempfile
import threading
import uuid
import hou
from PySide6 import QtCore, QtWidgets
from submit_render import Client, CONFIG, export_bundle, load_config, save_config

class RemoteRender(QtWidgets.QDialog):
    delivered = QtCore.Signal(object)

    def __init__(self):
        super().__init__(hou.qt.mainWindow())
        self.setWindowTitle('Remote Render')
        self.resize(650, 600)
        self.cfg = load_config()
        self.fields = {}
        self.jobs = dict(self.cfg.get('jobs', {}))
        self.inflight = False
        form = QtWidgets.QFormLayout(self)
        for key, label, default in [('host', 'Linux host / Tailscale IP', ''), ('username', 'SSH username', ''), ('scene', 'Trusted scene (.hip / .hiplc)', hou.hipFile.path()), ('lop', 'Solaris LOP path', '/stage/OUT'), ('output', 'Windows output directory', str(Path.home() / 'renders')), ('job', 'Job ID', self.cfg.get('last_job', ''))]:
            edit = QtWidgets.QLineEdit(str(self.cfg.get(key, default)))
            self.fields[key] = edit
            form.addRow(label, edit)
        self.renderer = QtWidgets.QComboBox()
        self.renderer.addItems(['xpu', 'cpu'])
        form.addRow('Karma engine', self.renderer)
        for key, default, low, high in [('start', 1, -100000, 100000), ('end', 1, -100000, 100000), ('step', 1, 1, 10000), ('width', 1920, 1, 32768), ('height', 1080, 1, 32768)]:
            spin = QtWidgets.QSpinBox()
            spin.setRange(low, high)
            spin.setValue(default)
            self.fields[key] = spin
            form.addRow(key.title(), spin)
        self.format = QtWidgets.QComboBox()
        self.format.addItems(['exr', 'png'])
        form.addRow('Output format', self.format)
        self.trust = QtWidgets.QCheckBox('I trust this scene and its assets (scenes can execute code).')
        form.addRow(self.trust)
        for label, action in [('Submit Render', self.submit), ('Cancel Render', lambda: self.remote('cancel')), ('Render Status', lambda: self.remote('status')), ('Download Results', lambda: self.remote('download'))]:
            button = QtWidgets.QPushButton(label)
            button.clicked.connect(action)
            form.addRow(button)
        self.status = QtWidgets.QPlainTextEdit()
        self.status.setReadOnly(True)
        form.addRow(self.status)
        self.delivered.connect(self.finished_request)
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(5000)

    def settings(self):
        return {'port': int(self.cfg.get('port', 22))} | {k: v.value() if isinstance(v, QtWidgets.QSpinBox) else v.text().strip() for k, v in self.fields.items()}

    def persist(self):
        settings = self.settings()
        save_config({k: settings[k] for k in ('host', 'username', 'port', 'lop', 'output')} | {'last_job': settings['job'], 'jobs': self.jobs})

    def async_call(self, fn, action, jid):
        if self.inflight:
            return
        self.inflight = True
        def work():
            try:
                value = fn()
                self.delivered.emit({'action': action, 'id': jid, 'value': value})
            except Exception as exc:
                self.delivered.emit({'action': action, 'id': jid, 'error': str(exc)})
        threading.Thread(target=work, daemon=True).start()

    def submit(self):
        if self.inflight:
            return
        s = self.settings()
        if not self.trust.isChecked():
            self.status.setPlainText('Acknowledge trust before loading/exporting the scene.')
            return
        try:
            if s['scene'].lower().endswith('.hipnc'):
                raise ValueError('Apprentice scenes are unsupported')
            scene = Path(s['scene'])
            if scene.resolve() != Path(hou.hipFile.path()).resolve():
                if hou.hipFile.hasUnsavedChanges():
                    raise ValueError('Save the current scene before selecting another scene')
                hou.hipFile.load(str(scene), suppress_save_prompt=False)
            from shared.job_schema import validate
            # Validate range before a potentially expensive export.
            if s['end'] < s['start'] or len(range(s['start'], s['end'] + 1, s['step'])) > 10000:
                raise ValueError('Invalid frame range')
            s.update(renderer=self.renderer.currentText(), format=self.format.currentText(), trusted=True)
            staging = Path(tempfile.gettempdir()) / ('hrr-' + uuid.uuid4().hex)
            self.status.setPlainText('Exporting Solaris frames and validating dependencies…')
            spec = export_bundle(s, staging)  # Houdini calls must stay on the UI thread.
            jid = spec['id']
            self.fields['job'].setText(jid)
            self.jobs[jid] = {'output': s['output'], 'host': s['host'], 'username': s['username'], 'downloaded': False}
            self.persist()
            def transfer():
                import shutil
                c = Client(s)
                try:
                    result = c.upload(staging)
                    shutil.rmtree(staging)
                    return result
                finally:
                    c.close()
            self.async_call(transfer, 'submit', jid)
        except Exception as exc:
            self.status.setPlainText(str(exc))

    def remote(self, action, jid=None):
        s = self.settings()
        jid = jid or s['job']
        record = self.jobs.get(jid, {})
        cfg = dict(s)
        cfg.update(record)
        def request():
            c = Client(cfg)
            try:
                if action == 'download':
                    return c.download(jid, record.get('output', s['output']))
                return c.rpc(action, jid)
            finally:
                c.close()
        self.async_call(request, action, jid)

    def poll(self):
        if self.inflight:
            return
        # Round robin tracks multiple submitted jobs while the panel is open.
        pending = [j for j, r in self.jobs.items() if not r.get('downloaded') and not r.get('terminal')]
        if pending:
            jid = pending.pop(0)
            record = self.jobs.pop(jid)
            self.jobs[jid] = record
            self.remote('status', jid)

    @QtCore.Slot(object)
    def finished_request(self, result):
        self.inflight = False
        self.status.setPlainText(json.dumps(result, indent=2))
        jid = result['id']
        if 'error' in result:
            return
        value = result['value']
        if result['action'] == 'status' and value.get('status') == 'completed':
            self.remote('download', jid)
        elif result['action'] == 'status' and value.get('status') in ('failed', 'cancelled'):
            if jid in self.jobs:
                self.jobs[jid]['terminal'] = True
                self.persist()
        elif result['action'] == 'download' and jid in self.jobs:
            self.jobs[jid]['downloaded'] = True
            self.persist()

_dialog = None

def show():
    global _dialog
    if _dialog is None:
        _dialog = RemoteRender()
    _dialog.show()
    _dialog.raise_()
