#!/usr/bin/env python3
"""Generate PCM update indexes offline. Never uploads or modifies KiCad settings."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from urllib.parse import urlsplit
from zipfile import BadZipFile, ZipFile

from package_plugin import ROOT, atomic_write, json_bytes, validate_manifest, validate_schema


def http_url(value):
    parsed = urlsplit(value)
    if (parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username is not None
            or parsed.password is not None or parsed.fragment or '\\' in value or any(c.isspace() for c in value)):
        raise ValueError('Expected an HTTP(S) URL without credentials, whitespace or fragment')
    return value


def version_key(version):
    parts = tuple(int(value) for value in version['version'].split('.'))
    return (version.get('version_epoch', 0),) + parts + (0,) * (3 - len(parts))


def validate_indexes(value, definition):
    for schema in ('pcm.v1.schema.json', 'pcm.v2.schema.json'):
        validate_schema(value, schema, definition)
    if definition == 'PackageArray':
        identifiers = set()
        for package in value['packages']:
            if package['identifier'] in identifiers:
                raise ValueError('Duplicate package identifier')
            identifiers.add(package['identifier'])
            versions = set()
            for version in package['versions']:
                key = version_key(version)
                if key in versions:
                    raise ValueError('Duplicate package version')
                versions.add(key)
                for field in ('download_url', 'download_sha256', 'download_size', 'install_size'):
                    if field not in version:
                        raise ValueError('Repository release is missing ' + field)
                http_url(version['download_url'])


def build_repository(archive_path, output_dir, base_url, download_url, previous_packages=None, timestamp=None):
    http_url(base_url)
    http_url(download_url)
    if urlsplit(base_url).query:
        raise ValueError('Repository base URL must be a directory without a query')
    archive_path, output = Path(archive_path), Path(output_dir)
    with ZipFile(archive_path) as archive:
        names = archive.namelist()
        if sum(info.file_size for info in archive.infolist()) > 64 * 1024 * 1024:
            raise ValueError('Unexpectedly large Backport release')
        if len(names) != len(set(names)) or archive.testzip():
            raise ValueError('Invalid ZIP entries or checksum')
        if any('\\' in name or ':' in name or any(p in ('', '.', '..') for p in name.split('/'))
               or (name != 'metadata.json' and not name.startswith('plugins/')) for name in names):
            raise ValueError('Not a safe unified PCM archive')
        metadata = json.loads(archive.read('metadata.json'))
        entries = {name[8:]: archive.read(name) for name in names if name.startswith('plugins/')}
    for schema in ('pcm.v1.schema.json', 'pcm.v2.schema.json'):
        validate_schema(metadata, schema)
    manifest = validate_manifest(entries)
    expected_id = json.loads((ROOT / 'plugin.json').read_text(encoding='utf-8'))['identifier']
    if metadata['identifier'] != expected_id or manifest['identifier'] != expected_id or len(metadata['versions']) != 1:
        raise ValueError('Expected a single-version KiCad Backport release')
    version = metadata['versions'][0]
    if (version['version'] != manifest['version'] or version.get('runtime') != 'ipc'
            or version['kicad_version'] != '6.0' or version.get('kicad_version_max') != '10.99'
            or version.get('install_size') != sum(map(len, entries.values()))
            or any(name.startswith('download_') for name in version)):
        raise ValueError('Expected unified PCM metadata without download fields')
    for name in ('__init__.py', 'legacy/kicad_backport_action.py', 'requirements.txt', 'LICENSE'):
        if name not in entries:
            raise ValueError('Missing PCM runtime file: ' + name)
    digest = hashlib.sha256()
    with archive_path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    version.update(download_url=download_url, download_sha256=digest.hexdigest(), download_size=archive_path.stat().st_size)

    history = Path(previous_packages) if previous_packages is not None else output / 'packages.json'
    packages = json.loads(history.read_text(encoding='utf-8')) if previous_packages is not None or history.exists() else {'packages': []}
    validate_indexes(packages, 'PackageArray')
    for index, old in enumerate(packages['packages']):
        if old['identifier'] != expected_id:
            continue
        for release in old['versions']:
            if version_key(release) == version_key(version):
                if any(release.get(key) != version.get(key) for key in ('download_sha256', 'download_size')):
                    raise ValueError('Published version has different bytes; bump the source version')
            else:
                metadata['versions'].append(release)
        packages['packages'].pop(index)
        break
    metadata['versions'].sort(key=version_key, reverse=True)
    packages['packages'].append(metadata)
    packages['packages'].sort(key=lambda package: package['identifier'])
    validate_indexes(packages, 'PackageArray')
    packages_data = json_bytes(packages)
    packages_hash = hashlib.sha256(packages_data).hexdigest()
    # Immutable index name lets publishers upload files before switching the root.
    index_name = 'packages-' + packages_hash + '.json'
    index_url = base_url.rstrip('/') + '/' + index_name
    root_path = output / 'repository.json'
    previous = json.loads(root_path.read_text(encoding='utf-8')) if root_path.exists() else None
    if previous:
        validate_indexes(previous, 'Repository')
    old = previous['packages'] if previous else {}
    changed = old.get('sha256') != packages_hash or old.get('url') != index_url
    old_timestamp = old.get('update_timestamp', 0)
    if timestamp is None:
        timestamp = max(int(time.time()), old_timestamp + 1) if changed else old_timestamp
    if isinstance(timestamp, bool) or not isinstance(timestamp, int) or timestamp < 0:
        raise ValueError('Timestamp must be a nonnegative Unix integer')
    if old and (timestamp < old_timestamp or (changed and timestamp == old_timestamp)):
        raise ValueError('Changed indexes require a strictly increasing timestamp')
    repository = {
        '$schema': 'https://go.kicad.org/pcm/schemas/v1',
        'name': 'KiCad Backport PCM repository', 'maintainer': metadata['author'],
        'packages': {'url': index_url, 'sha256': packages_hash, 'update_timestamp': timestamp,
                     'update_time_utc': datetime.fromtimestamp(timestamp, timezone.utc).strftime('%Y-%m-%d %H:%M:%S')},
    }
    validate_indexes(repository, 'Repository')
    atomic_write(output / index_name, packages_data)
    atomic_write(output / 'packages.json', packages_data)  # Editable history input, not the live pointer.
    atomic_write(root_path, json_bytes(repository))
    return root_path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True)
    parser.add_argument('--output', default='dist/pcm-repository')
    parser.add_argument('--base-url', required=True, help='Public HTTP(S) index directory')
    parser.add_argument('--download-url', required=True, help='Direct URL of the versioned PCM ZIP, not a release page')
    parser.add_argument('--previous-packages', help='Existing packages.json; retain all older releases')
    parser.add_argument('--timestamp', type=int)
    args = parser.parse_args(argv)
    try:
        print(build_repository(args.archive, args.output, args.base_url, args.download_url,
                               args.previous_packages, args.timestamp))
    except (OSError, ValueError, RuntimeError, KeyError, BadZipFile, OverflowError) as error:
        parser.exit(1, 'Repository build failed: {}\n'.format(error))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
