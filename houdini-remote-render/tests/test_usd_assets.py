import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from windows.submit_render import Bundle

@unittest.skipUnless(importlib.util.find_spec('pxr'), 'Requires Houdini USD bindings or optional usd-core test environment')
class AssetPackaging(unittest.TestCase):
    def test_nested_layer_and_texture_relocated(self):
        from pxr import Sdf, Usd, UsdUtils
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            source, dest = base / 'source', base / 'dest'
            source.mkdir()
            dest.mkdir()
            (source / 'texture.exr').write_bytes(b'fake texture data')
            layer = Sdf.Layer.CreateNew(str(source / 'child.usda'))
            prim = Sdf.CreatePrimInLayer(layer, '/World')
            attr = Sdf.AttributeSpec(prim, 'texture', Sdf.ValueTypeNames.Asset)
            attr.default = Sdf.AssetPath('texture.exr')
            layer.Save()
            root = Sdf.Layer.CreateNew(str(source / 'root.usda'))
            root.subLayerPaths = ['child.usda']
            root.Save()
            packed = Bundle(dest).add(source / 'root.usda')
            self.assertEqual(UsdUtils.ComputeAllDependencies(str(dest / packed))[2], [])
            # Remove originals so resolver fallback cannot mask broken remapping.
            import shutil
            shutil.rmtree(source)
            self.assertTrue(Usd.Stage.Open(str(dest / packed)))
            self.assertEqual(UsdUtils.ComputeAllDependencies(str(dest / packed))[2], [])

    def test_missing_usd_dependency_is_rejected(self):
        from pxr import Sdf
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            root = Sdf.Layer.CreateNew(str(base / 'root.usda'))
            prim = Sdf.CreatePrimInLayer(root, '/World')
            Sdf.AttributeSpec(prim, 'texture', Sdf.ValueTypeNames.Asset).default = Sdf.AssetPath('missing.exr')
            root.Save()
            with self.assertRaisesRegex(ValueError, 'Unresolved'):
                Bundle(base / 'out').add(base / 'root.usda')

    def test_materialx_and_udim(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            for tile in (1001, 1002):
                (base / ('glass.%d.exr' % tile)).write_bytes(b'tile')
            (base / 'glass.mtlx').write_text('<materialx><image name="img" type="color3"><input name="file" type="filename" value="glass.&lt;UDIM&gt;.exr" /></image></materialx>')
            dest = base / 'out'
            bundle = Bundle(dest)
            name = bundle.add(base / 'glass.mtlx')
            self.assertEqual(len(list(dest.rglob('*.exr'))), 2)
            self.assertTrue((dest / name).exists())

    def test_glass_fixture(self):
        from pxr import Usd, UsdRender
        stage = Usd.Stage.Open(str(Path(__file__).with_name('glass.usda')))
        self.assertEqual(len([p for p in stage.Traverse() if p.IsA(UsdRender.Settings)]), 1)
        self.assertEqual(stage.GetPrimAtPath('/World/glass/surface').GetAttribute('info:id').Get(), 'ND_standard_surface_surfaceshader')

    def test_houdini_export_contract_with_real_usd(self):
        from pxr import Usd
        from types import SimpleNamespace
        from unittest.mock import patch
        from windows.submit_render import export_bundle
        from shared.job_schema import validate
        stage = Usd.Stage.Open(str(Path(__file__).with_name('glass.usda')))
        category = object()
        node = SimpleNamespace(type=lambda: SimpleNamespace(category=lambda: category), stage=lambda: stage)
        hou = SimpleNamespace(applicationVersion=lambda: (22, 0, 0), licenseCategory=lambda: 'Commercial', lopNodeTypeCategory=lambda: category, node=lambda _: node, frame=lambda: 1, setFrame=lambda _: None, hipFile=SimpleNamespace(path=lambda: 'fixture.hip', save=lambda: None))
        with tempfile.TemporaryDirectory() as d, patch.dict(sys.modules, {'hou': hou}):
            settings = dict(trusted=True, lop='/stage/OUT', renderer='xpu', start=1, end=3, step=1, width=128, height=128, format='exr')
            spec = export_bundle(settings, Path(d) / 'bundle')
            self.assertEqual(validate(spec), [1, 2, 3])
            self.assertEqual(len(spec['frames']), 3)
            hou.licenseCategory = lambda: 'Apprentice'
            with self.assertRaisesRegex(ValueError, 'Apprentice'):
                export_bundle(settings, Path(d) / 'refused')
