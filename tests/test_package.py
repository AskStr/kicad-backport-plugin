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
                for name in ('package_plugin.py', '__init__.py', 'plugin.json', 'requirements.txt', 'README.md', 'LICENSE'):
                    shutil.copyfile(ROOT/name, source/name)
                for name in ('plugin', 'legacy', 'assets', 'docs', 'pcm'):
                    shutil.copytree(ROOT/name, source/name, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo'))
                version = json.loads((source/'plugin.json').read_bytes())['version']
                command = [sys.executable, str(source/'package_plugin.py')]
                if format is not None:
                    command += ['--format', format]
                # No shell=True: this also exercises paths outside the repo.
                result = subprocess.run(command, cwd=base, capture_output=True, text=True, timeout=30)
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
                if has_zip:
                    with ZipFile(manual_zip) as archive:
                        self.assertIsNone(archive.testzip())
                        self.assertIn('kicad-backport/plugin.json', archive.namelist())
                if has_tar:
                    with tarfile.open(manual_tar, 'r:gz') as archive:
                        self.assertIn('kicad-backport/plugin.json', archive.getnames())
                result = subprocess.run(command + ['--version', version], cwd=base,
                                        capture_output=True, text=True, timeout=30)
                self.assertEqual(0, result.returncode, result.stderr)
                if has_pcm:
                    self.assertEqual(original, pcm.read_bytes())
                result = subprocess.run(command + ['--version', '0.0.0'], cwd=base,
                                        capture_output=True, text=True, timeout=30)
                self.assertNotEqual(0, result.returncode)
                self.assertIn('does not match', result.stderr)
                if has_pcm:
                    self.assertEqual(original, pcm.read_bytes())

    def test_repository_cli_uses_existing_archive_from_another_directory(self):
        with tempfile.TemporaryDirectory(prefix='Backport Python repository ') as temp:
            base = Path(temp)
            archive = base/'release.zip'
            result = subprocess.run([sys.executable, str(ROOT/'package_plugin.py'), '--output', str(archive)],
                                    cwd=base, capture_output=True, text=True, timeout=30)
            self.assertEqual(0, result.returncode, result.stderr)
            original = archive.read_bytes()
            result = subprocess.run([
                sys.executable, str(ROOT/'package_repository.py'), '--archive', 'release.zip',
                '--output', 'repository', '--base-url', 'https://example.org/pcm',
                '--download-url', 'https://example.org/releases/release.zip',
            ], cwd=base, capture_output=True, text=True, timeout=30)
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
