"""PCM layout, registration, and offline update lifecycle regressions."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from package_plugin import ROOT, build_archive, build_manual, json_bytes, validate_schema, zip_bytes
from package_repository import build_repository, version_key


class PcmTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = tempfile.TemporaryDirectory(prefix='Backport PCM 中文 ')
        cls.base = Path(cls.workspace.name)
        cls.archive = build_archive(output_path=cls.base / 'release.zip')
        with ZipFile(cls.archive) as archive:
            cls.entries = {name: archive.read(name) for name in archive.namelist()}
        cls.metadata = json.loads(cls.entries['metadata.json'])
        cls.installed = cls.base / 'third-party/plugins' / cls.metadata['identifier'].replace('.', '_')
        for name, data in cls.entries.items():
            if name.startswith('plugins/'):
                path = cls.installed / name[8:]
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)

    @classmethod
    def tearDownClass(cls):
        cls.workspace.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=self.base)
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def publish(self, archive=None, **kwargs):
        options = dict(archive_path=archive or self.archive, output_dir=self.directory / 'repo',
                       base_url='https://example.org/pcm', download_url='https://example.org/releases/0.4.5.zip')
        options.update(kwargs)
        return build_repository(**options)

    def mutated_archive(self, mutate):
        entries = dict(self.entries)
        mutate(entries)
        path = self.directory / 'modified.zip'
        path.write_bytes(zip_bytes(entries))
        return path

    def test_schemas_layout_and_install_size(self):
        for schema in ('pcm.v1.schema.json', 'pcm.v2.schema.json'):
            validate_schema(self.metadata, schema)
        version = self.metadata['versions'][0]
        self.assertEqual(('6.0', '10.99', 'ipc'), (version['kicad_version'], version['kicad_version_max'], version['runtime']))
        self.assertFalse(any(key.startswith('download_') for key in version))
        self.assertEqual(sum(len(data) for name, data in self.entries.items() if name.startswith('plugins/')), version['install_size'])
        self.assertEqual((ROOT/'pcm/entrypoint.py').read_bytes(), self.entries['plugins/__init__.py'])
        self.assertNotEqual((ROOT/'__init__.py').read_bytes(), self.entries['plugins/__init__.py'])
        self.assertIn('plugins/LICENSE', self.entries)
        for name in self.entries:
            self.assertTrue(name == 'metadata.json' or name.startswith('plugins/'))
            self.assertNotIn('\\', name)
            self.assertNotIn('__pycache__', name)
            self.assertFalse(name.endswith(('.pyc', '.pyo')))
            self.assertNotIn('/tests/', name)

    def test_deterministic_build_and_immutable_output(self):
        second = build_archive(output_path=self.directory / 'same.zip')
        self.assertEqual(self.archive.read_bytes(), second.read_bytes())
        with self.assertRaises(ValueError):
            build_archive(output_path=second, status='testing')
        self.assertEqual(self.archive.read_bytes(), second.read_bytes())

    def test_isolated_installed_cli(self):
        result = subprocess.run([sys.executable, '-E', str(self.installed/'plugin/plugin.py'), '--list-targets'],
                                cwd=self.directory, capture_output=True, text=True, timeout=30)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn('10.0', result.stdout)

    def registration(self, version, api, config_text=None, settings_manager=False):
        config_root = self.directory / 'settings'
        config = config_root / version
        config.mkdir(parents=True, exist_ok=True)
        (config/'kicad_common.json').write_text(config_text if config_text is not None else json.dumps({'api': {'enable_server': api}}), encoding='utf-8')
        code = r'''
import importlib, os, sys, types
sys.path.insert(0, sys.argv[1])
os.environ['KICAD_CONFIG_HOME'] = sys.argv[3]
registered = []
class ActionPlugin:
    def __init__(self): self.defaults()
    def register(self): registered.append(self)
pcb = types.ModuleType('pcbnew')
pcb.ActionPlugin = ActionPlugin
pcb.GetBuildVersion = lambda: sys.argv[4] + '.7'
if sys.argv[5] == 'True':
    pcb.GetSettingsManager = lambda: types.SimpleNamespace(GetUserSettingsPath=lambda: os.path.join(sys.argv[3], sys.argv[4]))
    os.environ['KICAD_CONFIG_HOME'] = 'wrong-config-root'
sys.modules['pcbnew'] = pcb
sys.modules['wx'] = None
sys.modules['tkinter'] = None
importlib.import_module(sys.argv[2])
print(len(registered))
'''
        result = subprocess.run([sys.executable, '-I', '-B', '-c', code, str(self.installed.parent), self.installed.name,
                                 str(config_root), version, str(settings_manager)],
                                cwd=self.directory, capture_output=True, text=True, timeout=30)
        self.assertEqual(0, result.returncode, result.stderr)
        return int(result.stdout.strip())

    def test_swig_ipc_selection_matrix(self):
        for version in ('6.0', '7.0', '8.0', '9.0', '10.0', '10.99'):
            for api in (False, True):
                with self.subTest(version=version, api=api):
                    self.assertEqual(0 if api and int(version.split('.')[0]) >= 9 else 1, self.registration(version, api))

    def test_settings_manager_precedes_environment(self):
        self.assertEqual(0, self.registration('10.0', True, settings_manager=True))

    def test_bad_settings_fall_back_without_importing_gui(self):
        for text in ('not-json', 'null', '[]', '{"api":null}', '{"api":{"enable_server":"true"}}'):
            with self.subTest(text=text):
                self.assertEqual(1, self.registration('10.0', False, text))

    def test_ipc_only_import(self):
        code = "import sys,importlib;sys.path.insert(0,sys.argv[1]);sys.modules['pcbnew']=None;importlib.import_module(sys.argv[2])"
        result = subprocess.run([sys.executable, '-I', '-c', code, str(self.installed.parent), self.installed.name],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(0, result.returncode, result.stderr)

    def test_platform_config_and_active_version_isolation(self):
        spec = importlib.util.spec_from_file_location('pcm_entrypoint_test', ROOT/'pcm/entrypoint.py')
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'pcbnew': None}):
            spec.loader.exec_module(module)
        host = types.SimpleNamespace(GetBuildVersion=lambda: '10.0.4')
        for platform in ('win32', 'darwin', 'linux'):
            with self.subTest(platform=platform), patch.object(module.sys, 'platform', platform), patch.dict(os.environ, {}, clear=True), patch.object(module.os.path, 'expanduser', side_effect=lambda value: str(self.directory) if value == '~' else value):
                if platform == 'win32':
                    base = self.directory/'AppData/Roaming/kicad'
                elif platform == 'darwin':
                    base = self.directory/'Library/Preferences/kicad'
                else:
                    base = self.directory/'.config/kicad'
                for version, api in (('10.0', False), ('10.99', True)):
                    config = base/version
                    config.mkdir(parents=True, exist_ok=True)
                    (config/'kicad_common.json').write_text(json.dumps({'api': {'enable_server': api}}))
                self.assertFalse(module._use_ipc(host))
                (base/'10.0/kicad_common.json').write_text('{"api":{"enable_server":true}}')
                self.assertTrue(module._use_ipc(host))

    def test_repository_hashes_and_noop(self):
        path = self.publish(timestamp=1788652800)
        original = path.read_bytes()
        repo = json.loads(original)
        packages = self.directory/'repo/packages.json'
        self.assertEqual(hashlib.sha256(packages.read_bytes()).hexdigest(), repo['packages']['sha256'])
        self.assertEqual(packages.read_bytes(), (path.parent/repo['packages']['url'].rsplit('/',1)[1]).read_bytes())
        release = json.loads(packages.read_bytes())['packages'][0]['versions'][0]
        self.assertEqual(hashlib.sha256(self.archive.read_bytes()).hexdigest(), release['download_sha256'])
        self.assertEqual(self.archive.stat().st_size, release['download_size'])
        self.publish()
        self.assertEqual(original, path.read_bytes())

    def test_history_updates_and_immutable_versions(self):
        self.publish(timestamp=1788652800)
        history_path = self.directory/'repo/packages.json'
        history = json.loads(history_path.read_bytes())
        release = history['packages'][0]['versions'][0]
        release['version'] = '0.4.4'
        history_path.write_bytes(json_bytes(history))
        path = self.publish(timestamp=1788652801)
        releases = json.loads(history_path.read_bytes())['packages'][0]['versions']
        self.assertEqual(['0.4.5','0.4.4'], [item['version'] for item in releases])
        releases[0]['download_sha256'] = '0'*64
        history = json.loads(history_path.read_bytes())
        history['packages'][0]['versions'] = releases
        history_path.write_bytes(json_bytes(history))
        before = path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'different bytes'):
            self.publish()
        self.assertEqual(before, path.read_bytes())

    def test_timestamp_change_required_and_invalid_urls(self):
        path = self.publish(timestamp=1788652800)
        before = path.read_bytes()
        with self.assertRaises(ValueError):
            self.publish(timestamp=1788652800, download_url='https://example.org/new-location.zip')
        for value in ('file:///tmp/repo', 'https://user:pass@example.org/repo', 'https://example.org/#x'):
            with self.subTest(url=value), self.assertRaises(ValueError):
                self.publish(base_url=value)
        self.assertEqual(before, path.read_bytes())

    def test_numeric_order(self):
        values = [{'version': '0.4.9'}, {'version': '0.4.10'}, {'version':'0.1', 'version_epoch':1}]
        self.assertEqual(['0.1','0.4.10','0.4.9'], [v['version'] for v in sorted(values,key=version_key,reverse=True)])

    def test_archive_rejects_unsafe_paths_and_inconsistent_versions(self):
        bad = self.mutated_archive(lambda entries: entries.update({'plugins/../escape': b'bad'}))
        with self.assertRaises(ValueError):
            self.publish(bad)
        def mismatch(entries):
            manifest = json.loads(entries['plugins/plugin.json'])
            manifest['version'] = '0.0.1'
            entries['plugins/plugin.json'] = json_bytes(manifest)
        bad = self.mutated_archive(mismatch)
        with self.assertRaises(ValueError):
            self.publish(bad)

    def test_manual_package_is_not_a_pcm_release(self):
        path = self.directory/'manual.zip'
        path.write_bytes(zip_bytes({'kicad-backport/plugin.json': b'{}'}))
        with self.assertRaises(ValueError):
            self.publish(path)

    def test_source_validation_and_manual_output_preserves_history(self):
        source = self.directory/'source'
        source.mkdir()
        for name in ('__init__.py','plugin.json','requirements.txt','README.md','LICENSE'):
            shutil.copyfile(ROOT/name, source/name)
        for name in ('plugin','legacy','assets','docs','pcm'):
            shutil.copytree(ROOT/name, source/name, ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        output = source/'dist'
        output.mkdir()
        sentinel = output/'older-release.zip'
        sentinel.write_bytes(b'history')
        build_manual(source, 'all')
        self.assertEqual(b'history', sentinel.read_bytes())
        with ZipFile(output/'kicad-backport.zip') as archive:
            self.assertEqual((ROOT/'__init__.py').read_bytes(), archive.read('kicad-backport/__init__.py'))
        manifest = json.loads((source/'plugin.json').read_bytes())
        manifest['actions'][0]['entrypoint'] = '../outside.py'
        (source/'plugin.json').write_bytes(json_bytes(manifest))
        with self.assertRaises(ValueError):
            build_archive(source, output/'invalid.zip')
        self.assertFalse((output/'invalid.zip').exists())


if __name__ == '__main__':
    unittest.main()
