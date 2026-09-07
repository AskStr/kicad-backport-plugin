#!/usr/bin/env python3
"""Build deterministic KiCad 6–10.99 PCM ZIPs and traditional manual packages."""

import argparse
import ast
import io
import json
from pathlib import Path, PurePosixPath
import re
import struct
import tarfile
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parent


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode('utf-8')


def validate_schema(value, filename, definition=None, root=ROOT):
    try:
        from jsonschema import Draft7Validator
    except ImportError as error:
        raise RuntimeError('Install build dependencies: python -m pip install -r requirements-dev.txt') from error
    schema = json.loads((root / 'pcm/schemas' / filename).read_text(encoding='utf-8'))
    if definition:
        schema['$ref'] = '#/definitions/' + definition
    Draft7Validator.check_schema(schema)
    errors = list(Draft7Validator(schema).iter_errors(value))
    if errors:
        raise ValueError('{}: {}'.format(filename, errors[0].message))


def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name, suffix='.tmp', delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(data)
        except BaseException:
            stream.close()
            temporary.unlink()
            raise
    try:
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def runtime_files(root):
    names = {'__init__.py', 'plugin.json', 'requirements.txt', 'README.md', 'LICENSE',
             'legacy/__init__.py', 'legacy/kicad_backport_action.py',
             'plugin/plugin.py', 'plugin/backport_core.py', 'plugin/i18n.py'}
    for directory in ('plugin', 'legacy', 'assets', 'docs'):
        names.update(path.relative_to(root).as_posix() for path in (root / directory).rglob('*')
                     if path.is_file() and '__pycache__' not in path.parts and path.suffix not in ('.pyc', '.pyo'))
    entries = {}
    for name in sorted(names):
        path = root / name
        if root.resolve() not in path.resolve().parents:
            raise ValueError('Package file escapes source root: ' + name)
        entries[name] = path.read_bytes()
    return entries


def validate_manifest(entries, root=ROOT):
    manifest = json.loads(entries['plugin.json'])
    validate_schema(manifest, 'api.v1.schema.json', root=root)
    if not re.fullmatch(r'[A-Za-z]{2,}(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?){2,}', manifest['identifier']):
        raise ValueError('IPC identifier must be strict reverse DNS')
    if manifest['runtime']['type'] != 'python' or not manifest['actions']:
        raise ValueError('Expected Python runtime with actions')
    identifiers = [action['identifier'] for action in manifest['actions']]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError('Duplicate IPC action identifier')
    for action in manifest['actions']:
        for name in [action['entrypoint']] + action.get('icons-light', []) + action.get('icons-dark', []):
            path = PurePosixPath(name)
            if (path.is_absolute() or '\\' in name or ':' in name
                    or any(part in ('', '.', '..') for part in name.split('/')) or name not in entries):
                raise ValueError('Missing or unsafe IPC resource: ' + name)
    tree = ast.parse(entries['plugin/backport_core.py'])
    versions = [ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == 'VERSION' for target in node.targets)]
    if versions != [manifest['version']]:
        raise ValueError('plugin.json version must match backport_core.VERSION')
    return manifest


def zip_bytes(entries):
    stream = io.BytesIO()
    with ZipFile(stream, 'w', compression=ZIP_DEFLATED) as archive:
        for name, data in sorted(entries.items()):
            info = ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = ZIP_DEFLATED
            archive.writestr(info, data, compresslevel=9)
    return stream.getvalue()


def validate_pcm_icon(data):
    # PCM uses a dedicated 64px PNG, not plugin.json's toolbar icons.
    if (len(data) < 33 or data[:16] != b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'
            or struct.unpack('>II', data[16:24]) != (64, 64)):
        raise ValueError('PCM icon must be a 64x64 PNG')
    return data


def build_archive(source_root=ROOT, output_path=None, status='stable'):
    root = Path(source_root).resolve()
    entries = runtime_files(root)
    manifest = validate_manifest(entries, root)
    entries['__init__.py'] = (root / 'pcm/entrypoint.py').read_bytes()
    icon = validate_pcm_icon((root / 'pcm/icon.png').read_bytes())
    metadata = {
        '$schema': 'https://go.kicad.org/pcm/schemas/v1',
        'name': manifest['name'], 'identifier': manifest['identifier'],
        'type': 'plugin', 'license': 'MIT',
        'author': {'name': 'askstar', 'contact': {'web': 'https://github.com/AskStr'}},
        'description': manifest['description'],
        'description_full': 'Create compatibility copies of KiCad files and projects. '
                            'One PCM package supports KiCad 6 through 10.99. '
                            'KiCad 6–8 and API-disabled 9–10 use pcbnew/wxPython. '
                            'API-enabled KiCad 9+ uses the Python action; KiCad 10.99 requires the API. '
                            'Python 3.8 or later is required; external Python must provide tkinter/Tcl/Tk or wxPython, venv and pip. '
                            'No third-party pip dependencies are required by the converter.',
        'resources': {'homepage': 'https://github.com/AskStr/kicad-backport-plugin',
                      'issues': 'https://github.com/AskStr/kicad-backport-plugin/issues'},
        'tags': ['backport', 'conversion', 'compatibility'],
        'versions': [{'version': manifest['version'], 'status': status, 'runtime': 'ipc',
                      'kicad_version': '6.0', 'kicad_version_max': '10.99',
                      'install_size': sum(map(len, entries.values())) + len(icon)}],
    }
    for schema in ('pcm.v1.schema.json', 'pcm.v2.schema.json'):
        validate_schema(metadata, schema, root=root)
    payload = {'plugins/' + name: data for name, data in entries.items()}
    payload['metadata.json'] = json_bytes(metadata)
    payload['resources/icon.png'] = icon
    output = Path(output_path or root / 'dist' / ('kicad-backport-v' + manifest['version'] + '-PCM.zip')).resolve()
    if output.suffix.lower() != '.zip':
        raise ValueError('PCM output must be a ZIP')
    data = zip_bytes(payload)
    # Versioned artifacts must not silently replace an existing release.
    if output.exists() and output.read_bytes() != data:
        raise ValueError('Output already contains different bytes; bump the version or use a new output path')
    atomic_write(output, data)
    return output


def build_manual(root=ROOT, format='zip'):
    entries = runtime_files(root)
    validate_manifest(entries, root)
    output = root / 'dist'
    payload = {'kicad-backport/' + name: data for name, data in entries.items()}
    results = []
    if format in ('zip', 'all'):
        path = output / 'kicad-backport.zip'
        atomic_write(path, zip_bytes(payload))
        results.append(path)
    if format in ('tar.gz', 'all'):
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode='w:gz') as archive:
            for name, data in sorted(payload.items()):
                info = tarfile.TarInfo(name)
                info.size, info.mode, info.mtime = len(data), 0o644, 1577836800
                archive.addfile(info, io.BytesIO(data))
        path = output / 'kicad-backport.tar.gz'
        atomic_write(path, stream.getvalue())
        results.append(path)
    # Retain the unpacked convenience output without recursively deleting dist.
    for name, data in payload.items():
        atomic_write(output / name, data)
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('version', nargs='?', help='Assert source version (does not rewrite it)')
    parser.add_argument('--version', '-v', dest='expected_version')
    parser.add_argument('--format', '-f', choices=('pcm', 'zip', 'tar.gz', 'all'), default='pcm')
    parser.add_argument('--output', '-o', help='PCM ZIP output path')
    parser.add_argument('--archive', help='Reuse an existing published PCM ZIP without rebuilding it')
    parser.add_argument('--repository', action='store_true', help='Also prepare the existing PCM update feed; URLs are derived automatically')
    parser.add_argument('--status', choices=('stable', 'testing', 'development', 'deprecated'), default='stable')
    args = parser.parse_args(argv)
    manifest = json.loads((ROOT / 'plugin.json').read_text(encoding='utf-8'))
    for expected in (args.version, args.expected_version):
        if expected and expected != manifest['version']:
            parser.error('Requested version does not match plugin.json; update source versions first')
    if args.archive and (args.output or args.format != 'pcm'):
        parser.error('--archive cannot be combined with --output or manual package formats')
    if args.repository and args.format == 'tar.gz':
        parser.error('--repository requires a PCM ZIP')
    if args.output and args.format == 'tar.gz':
        parser.error('--output is only for PCM ZIPs')
    try:
        if args.format != 'tar.gz':
            from package_repository import prepare_release
            archive = Path(args.archive) if args.archive else build_archive(output_path=args.output, status=args.status)
            print(archive)
            for path in prepare_release(archive, repository=args.repository):
                print(path)
            if args.repository:
                print(archive.parent / 'pcm-repository/repository.json')
        if args.format != 'pcm':
            for path in build_manual(format=args.format):
                print(path)
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(1, 'Package build failed: {}\n'.format(error))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
