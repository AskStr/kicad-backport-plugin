"""Check a published PCM root, icons, version list and release downloads over HTTP.

Read-only: never installs plugins or changes KiCad settings. Build dependencies
are required for schema validation. Run this after uploading release assets.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
from urllib.request import Request, urlopen
from zipfile import BadZipFile, ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from package_plugin import validate_pcm_icon
from package_repository import http_url, validate_indexes, version_key


def fetch(url, limit=64 * 1024 * 1024):
    http_url(url)
    request = Request(url, headers={'User-Agent': 'KiCad-Backport-PCM-check', 'Cache-Control': 'no-cache'})
    with urlopen(request, timeout=30) as response:
        http_url(response.geturl())
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError('Download exceeds verification size limit: ' + url)
    return data


def checked_download(reference, size=None):
    data = fetch(reference['url'])
    if hashlib.sha256(data).hexdigest() != reference['sha256']:
        raise ValueError('SHA-256 mismatch: ' + reference['url'])
    if size is not None and len(data) != size:
        raise ValueError('Download size mismatch: ' + reference['url'])
    return data


def verify_repository(url):
    repository = json.loads(fetch(url, 1024 * 1024))
    validate_indexes(repository, 'Repository')
    packages = json.loads(checked_download(repository['packages']))
    validate_indexes(packages, 'PackageArray')
    identifier = json.loads((ROOT / 'plugin.json').read_text(encoding='utf-8'))['identifier']
    package = next((p for p in packages['packages'] if p['identifier'] == identifier), None)
    if package is None or not package['versions']:
        raise ValueError('Repository has no KiCad Backport releases')
    versions = package['versions']
    if versions != sorted(versions, key=version_key, reverse=True):
        raise ValueError('Versions must be ordered newest first')
    resources = checked_download(repository['resources'])
    with ZipFile(io.BytesIO(resources)) as archive:
        if archive.testzip():
            raise ValueError('Invalid resource ZIP checksum')
        icon = validate_pcm_icon(archive.read(identifier + '/icon.png'))
    for index, version in enumerate(versions):
        data = checked_download({'url': version['download_url'], 'sha256': version['download_sha256']},
                                version['download_size'])
        with ZipFile(io.BytesIO(data)) as archive:
            if archive.testzip():
                raise ValueError('Invalid release ZIP checksum')
            metadata = json.loads(archive.read('metadata.json'))
            release_versions = metadata['versions']
            if (metadata['identifier'] != identifier or len(release_versions) != 1
                    or release_versions[0]['version'] != version['version']):
                raise ValueError('Release metadata does not match the version index')
            install_size = sum(info.file_size for info in archive.infolist()
                               if info.filename.startswith(('plugins/', 'resources/')))
            if install_size != version['install_size'] or install_size != release_versions[0]['install_size']:
                raise ValueError('Release install size does not match the version index')
            if 'resources/icon.png' in archive.namelist():
                installed_icon = validate_pcm_icon(archive.read('resources/icon.png'))
                if index == 0 and installed_icon != icon:
                    raise ValueError('Latest installed icon differs from repository icon')
            elif index == 0:
                raise ValueError('Latest release has no installed PCM icon')
    return [version['version'] for version in versions]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', required=True, help='Published repository.json HTTP(S) URL, not a GitHub page')
    args = parser.parse_args(argv)
    try:
        versions = verify_repository(args.url)
    except (OSError, ValueError, KeyError, RuntimeError, BadZipFile) as error:
        parser.exit(1, 'PCM repository verification failed: {}\n'.format(error))
    print('PCM repository HTTP/hash/icon checks OK; versions: ' + ', '.join(versions))
    print('Native PCM GUI installation/update still requires acceptance testing.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
