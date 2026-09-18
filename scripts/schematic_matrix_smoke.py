"""Export repeatable upgrade/downgrade fixtures and compare native netlists.

Requires KiCad 7/8/9/10 under --kicad-root; V6 is read by V7 (not native V6).
All mismatches remain failures; exit 1 blocks a stable release. Output must be new.
Native CLI runs use temporary copies and never modify the exported test projects.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
from plugin import backport_core as core
from test_schematic_instances import netlist_signature, write_project


def snapshot(directory):
    return {p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in directory.rglob('*') if p.is_file()}


def serialize_signature(signature):
    return {'components': signature[0],
            'nets': {name: sorted(pins) for name, pins in signature[1].items()}}


def run_matrix(kicad_root, output):
    output.mkdir(parents=True, exist_ok=False)
    (output / 'netlists').mkdir()
    (output / 'reports').mkdir()
    tools = {}
    versions = {}
    for major in (7, 8, 9, 10):
        tools[major] = kicad_root / (str(major) + '.0') / 'bin/kicad-cli.exe'
        versions[str(major)] = subprocess.check_output(
            [str(tools[major]), 'version'], timeout=30).decode('utf-8').strip()

    def convert(source, name, major):
        before = snapshot(source)
        requested = output / name
        stdout, stderr, code = core.convert(
            source, requested, 'V' + str(major), output / 'reports' / (name + '.json'))
        if code:
            raise RuntimeError(name + ': ' + stdout + stderr)
        if before != snapshot(source):
            raise RuntimeError(name + ': source project was modified')
        return core.versioned_output_path(requested, 'V' + str(major))

    def export(project, name, major):
        # KiCad 6 predates kicad-cli; label this honestly as a V7 loader check.
        loader = max(7, major)
        destination = output / 'netlists' / (name + '.xml')
        with tempfile.TemporaryDirectory(prefix='backport-netlist-') as directory:
            copy = Path(directory) / 'project'
            shutil.copytree(project, copy)
            result = subprocess.run(
                [str(tools[loader]), 'sch', 'export', 'netlist', '--format', 'kicadxml',
                 '--output', str(destination), str(copy / 'issue4.kicad_sch')],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        log = (result.stdout + result.stderr).decode('utf-8', errors='replace')
        (output / 'netlists' / (name + '.log')).write_text(log, encoding='utf-8')
        if result.returncode:
            raise RuntimeError(name + ': native export failed: ' + log)
        return netlist_signature(destination)

    source = write_project(output / 'source_V10')
    original = snapshot(source)
    expected = export(source, 'source_V10', 10)
    cases = []

    def check(source, name, major, group):
        row = {'name': name, 'target': major, 'loader': max(7, major), 'group': group}
        project = None
        try:
            project = convert(source, name, major)
            row['project'] = project.relative_to(output).as_posix()
            actual = export(project, name, major)
            row['status'] = 'pass' if actual == expected else 'fail'
            row['actual'] = serialize_signature(actual)
            row['missing_references'] = sorted(set(expected[0]) - set(actual[0]))
            row['extra_references'] = sorted(set(actual[0]) - set(expected[0]))
        except (OSError, RuntimeError, subprocess.SubprocessError) as error:
            row['status'] = 'fail'
            row['error'] = str(error)
        cases.append(row)
        print(name + ': ' + row['status'], flush=True)
        return project

    sources = {10: source}
    for major in (6, 7, 8, 9):
        sources[major] = convert(source, 'source', major)
        if export(sources[major], 'source_V' + str(major), major) != expected:
            raise RuntimeError('Cannot use an electrically changed project as a matrix source')
    for from_major in (6, 7, 8, 9, 10):
        for to_major in (6, 7, 8, 9, 10):
            check(sources[from_major], 'V{}_to_V{}'.format(from_major, to_major),
                  to_major, 'schematic')
    assert snapshot(source) == original, 'Original fixture changed'
    report = {'version': core.VERSION, 'native_versions': versions,
              'expected': serialize_signature(expected), 'cases': cases,
              'passed': sum(row['status'] == 'pass' for row in cases),
              'failed': sum(row['status'] == 'fail' for row in cases),
              'scope': 'Synthetic fixture only; V6 uses V7 loader, not native V6.'}
    (output / 'matrix-report.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('{} passed, {} failed'.format(report['passed'], report['failed']))
    return 1 if report['failed'] else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kicad-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='New directory; existing data is never overwritten')
    args = parser.parse_args()
    return run_matrix(args.kicad_root.resolve(), args.output.resolve())


if __name__ == '__main__':
    raise SystemExit(main())
