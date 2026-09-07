"""Python packaging CLI regressions; no shell or external archive tools."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from zipfile import ZipFile

from package_plugin import ROOT


class PackageTests(unittest.TestCase):
    def test_python_only_packaging_from_another_directory(self):
        formats = (
            (None, True, False, False),
            ('pcm', True, False, False),
            ('zip', True, True, False),
            ('tar.gz', False, False, True),
            ('all', True, True, True),
        )
        for format, has_pcm, has_zip, has_tar in formats:
            with self.subTest(format=format), tempfile.TemporaryDirectory(prefix='Backport Python package ') as temp:
                base = Path(temp)
                source = base/'source'
                source.mkdir()
                for name in ('package_plugin.py', 'package_repository.py', '__init__.py', 'plugin.json', 'requirements.txt', 'README.md', 'LICENSE'):
                    shutil.copyfile(ROOT/name, source/name)
                for name in ('plugin', 'legacy', 'assets', 'docs', 'pcm'):
                    shutil.copytree(ROOT/name, source/name, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo'))
                version = json.loads((source/'plugin.json').read_bytes())['version']
                command = [sys.executable, str(source/'package_plugin.py')]
                if format is not None:
                    command += ['--format', format]
                # No shell=True: this also exercises paths outside the repo.
                result = subprocess.run(command, cwd=base, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=30)
                self.assertEqual(0, result.returncode, result.stderr)
                output = source/'dist'
                pcm = output/('kicad-backport-v' + version + '-PCM.zip')
                manual_zip = output/'kicad-backport.zip'
                manual_tar = output/'kicad-backport.tar.gz'
                self.assertEqual(has_pcm, pcm.is_file())
                self.assertEqual(has_zip, manual_zip.is_file())
                self.assertEqual(has_tar, manual_tar.is_file())
                self.assertEqual(has_zip or has_tar, (output/'kicad-backport/plugin.json').is_file())
                original = pcm.read_bytes() if has_pcm else None
                if has_pcm:
                    with ZipFile(pcm) as archive:
                        self.assertIsNone(archive.testzip())
                        self.assertIn('metadata.json', archive.namelist())
                    metadata = json.loads((output/'metadata.json').read_bytes())
                    self.assertEqual(version, metadata['versions'][0]['version'])
                    self.assertEqual(hashlib.sha256(original).hexdigest(), metadata['versions'][0]['download_sha256'])
                    self.assertTrue((output/'icon.png').is_file())
                if has_zip:
                    with ZipFile(manual_zip) as archive:
                        self.assertIsNone(archive.testzip())
                        self.assertIn('kicad-backport/plugin.json', archive.namelist())
                if has_tar:
                    with tarfile.open(manual_tar, 'r:gz') as archive:
                        self.assertIn('kicad-backport/plugin.json', archive.getnames())
                result = subprocess.run(command + ['--version', version], cwd=base,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=30)
                self.assertEqual(0, result.returncode, result.stderr)
                if has_pcm:
                    self.assertEqual(original, pcm.read_bytes())
                result = subprocess.run(command + ['--version', '0.0.0'], cwd=base,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=30)
                self.assertNotEqual(0, result.returncode)
                self.assertIn('does not match', result.stderr)
                if has_pcm:
                    self.assertEqual(original, pcm.read_bytes())

    def test_one_command_reuses_published_zip_and_prepares_update_feed(self):
        from package_plugin import build_archive
        with tempfile.TemporaryDirectory(prefix='Backport simple release ') as temp:
            base = Path(temp)
            archive = build_archive(output_path=base/'published.zip')
            original = archive.read_bytes()
            command = [sys.executable, str(ROOT/'package_plugin.py'), '--archive', str(archive), '--repository']
            for attempt in range(2):
                result = subprocess.run(command, cwd=base, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        universal_newlines=True, timeout=30)
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual(original, archive.read_bytes())
                metadata = json.loads((base/'metadata.json').read_bytes())
                release = metadata['versions'][0]
                self.assertEqual(('6.0', '10.99', 'ipc'),
                                 (release['kicad_version'], release['kicad_version_max'], release['runtime']))
                self.assertEqual(hashlib.sha256(original).hexdigest(), release['download_sha256'])
                self.assertEqual('https://github.com/AskStr/kicad-backport-plugin/releases/download/V' + release['version'] + '/published.zip', release['download_url'])
                repository = base/'pcm-repository/repository.json'
                if attempt:
                    self.assertEqual(previous, repository.read_bytes())
                previous = repository.read_bytes()
                self.assertEqual(metadata, json.loads((base/'pcm-repository/packages.json').read_bytes())['packages'][0])

    def test_official_metadata_keeps_history_and_rejects_changed_release(self):
        from package_plugin import build_archive, json_bytes
        from package_repository import prepare_release
        with tempfile.TemporaryDirectory(prefix='Backport official metadata ') as temp:
            base = Path(temp)
            archive = build_archive(output_path=base/'published.zip')
            path, icon = prepare_release(archive)
            old = json.loads(path.read_bytes())
            current_version = old['versions'][0]['version']
            old['versions'][0]['version'] = '0.4.6'
            path.write_bytes(json_bytes(old))
            prepare_release(archive)
            metadata = json.loads(path.read_bytes())
            self.assertEqual([current_version, '0.4.6'], [v['version'] for v in metadata['versions']])
            metadata['versions'][0]['download_sha256'] = '0'*64
            path.write_bytes(json_bytes(metadata))
            before = path.read_bytes()
            with self.assertRaisesRegex(ValueError, 'different bytes'):
                prepare_release(archive)
            self.assertEqual(before, path.read_bytes())

    def test_archive_mode_rejects_conflicting_output_options(self):
        with tempfile.TemporaryDirectory(prefix='Backport invalid options ') as temp:
            for options in (['--output', 'new.zip'], ['--format', 'all']):
                result = subprocess.run([sys.executable, str(ROOT/'package_plugin.py'), '--archive', 'missing.zip'] + options,
                                        cwd=temp, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        universal_newlines=True, timeout=30)
                self.assertNotEqual(0, result.returncode)
                self.assertIn('--archive cannot', result.stderr)
                self.assertFalse(list(Path(temp).iterdir()))

    def test_repository_cli_uses_existing_archive_from_another_directory(self):
        with tempfile.TemporaryDirectory(prefix='Backport Python repository ') as temp:
            base = Path(temp)
            archive = base/'release.zip'
            result = subprocess.run([sys.executable, str(ROOT/'package_plugin.py'), '--output', str(archive)],
                                    cwd=base, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=30)
            self.assertEqual(0, result.returncode, result.stderr)
            original = archive.read_bytes()
            result = subprocess.run([
                sys.executable, str(ROOT/'package_repository.py'), '--archive', 'release.zip',
                '--output', 'repository', '--base-url', 'https://example.org/pcm',
                '--download-url', 'https://example.org/releases/release.zip',
            ], cwd=base, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=30)
            self.assertEqual(0, result.returncode, result.stderr)
            repository = json.loads((base/'repository/repository.json').read_bytes())
            packages = (base/'repository/packages.json').read_bytes()
            self.assertEqual(hashlib.sha256(packages).hexdigest(), repository['packages']['sha256'])
            release = json.loads(packages)['packages'][0]['versions'][0]
            self.assertEqual(hashlib.sha256(original).hexdigest(), release['download_sha256'])
            self.assertEqual(original, archive.read_bytes())
            self.assertFalse((base/'dist').exists())


if __name__ == '__main__':
    unittest.main()
