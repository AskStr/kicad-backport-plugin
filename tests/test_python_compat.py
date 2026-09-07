"""Runtime checks runnable on the Python 3.8 baseline without build dependencies."""
import ast
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PythonCompatibilityTests(unittest.TestCase):
    def test_runtime_and_smoke_python38_syntax(self):
        paths = [ROOT / '__init__.py', ROOT / 'pcm/entrypoint.py']
        for directory in ('plugin', 'legacy', 'scripts'):
            paths.extend(sorted((ROOT / directory).glob('*.py')))
        paths.extend([Path(__file__), ROOT / 'tests/test_nightly_formats.py'])
        for path in paths:
            with self.subTest(path=str(path.relative_to(ROOT))):
                source = path.read_text(encoding='utf-8-sig')
                # Grammar checks do not check standard-library API compatibility.
                ast.parse(source, filename=str(path), feature_version=(3, 8))

    def test_manifest_python_minimum(self):
        manifest = json.loads((ROOT / 'plugin.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['runtime']['min_version'], '3.8')

    def run_cli(self, *args):
        # Explicit script path also works with the official isolated embeddable
        # interpreter, whose default sys.path omits the script directory.
        bootstrap = ('import os, runpy, sys; script=sys.argv.pop(1); '
                     'sys.path.insert(0, os.path.dirname(script)); '
                     'sys.argv[0]=script; runpy.run_path(script, run_name="__main__")')
        result = subprocess.run(
            [sys.executable, '-E', '-c', bootstrap, str(ROOT / 'plugin/plugin.py')] + list(args),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_cli_import_and_targets(self):
        result = self.run_cli('--list-targets')
        self.assertIn('6.0', result.stdout)
        self.assertIn('10.0', result.stdout)

    def test_cli_nightly_to_kicad6(self):
        with tempfile.TemporaryDirectory(prefix='backport_python_') as temp:
            directory = Path(temp)
            source = directory / 'nightly.kicad_pcb'
            output = directory / 'copy.kicad_pcb'
            report = directory / 'report.json'
            original = ('(kicad_pcb (version 20260831) (generator "pcbnew") '
                        '(layers (0 "F.Cu" signal) (2 "B.Cu" signal)) '
                        '(gr_line (start 10 10) (end 20 10) '
                        '(stroke (width 0.2) (type solid)) (layer "F.Cu") '
                        '(end_shape circle)))')
            source.write_text(original, encoding='utf-8')
            self.run_cli('--input', str(source), '--output', str(output),
                         '--target-version', '6.0', '--report', str(report))
            self.assertEqual(source.read_text(encoding='utf-8'), original)
            files = json.loads(report.read_text(encoding='utf-8'))['files']
            self.assertEqual(len(files), 1)
            # The CLI adds the target-version suffix to the requested output.
            from plugin.backport_core import versioned_output_path
            converted = versioned_output_path(output, '6.0').read_text(encoding='utf-8')
            self.assertIn('(version 20211014)', converted)
            self.assertNotIn('end_shape', converted)
            self.assertIn('gr_poly', converted)


if __name__ == '__main__':
    unittest.main()
