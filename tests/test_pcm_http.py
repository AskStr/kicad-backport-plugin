"""PCM HTTP lifecycle with real ZIPs and no external network or user settings."""
from functools import partial
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from zipfile import ZipFile

from package_plugin import build_archive, json_bytes, zip_bytes
from package_repository import build_repository
from scripts.pcm_repository_smoke import fetch, verify_repository


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class PcmHttpTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='backport_pcm_http_')
        self.addCleanup(temp.cleanup)
        self.directory = Path(temp.name)
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=temp.name))
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': 0.05}, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)
        self.base_url = 'http://127.0.0.1:{}'.format(self.server.server_port)
        self.archive = build_archive(output_path=self.directory / 'current.zip')
        with ZipFile(self.archive) as archive:
            self.entries = {name: archive.read(name) for name in archive.namelist()}
        self.metadata = json.loads(self.entries['metadata.json'])
        self.version = self.metadata['versions'][0]['version']
        self.repository_url = self.base_url + '/repository/repository.json'

    def stop_server(self):
        self.server.shutdown()
        self.thread.join(timeout=5)
        self.server.server_close()

    def publish(self, archive=None, timestamp=1788746400):
        archive = archive or self.archive
        return build_repository(archive, self.directory / 'repository', self.base_url + '/repository',
                                self.base_url + '/' + archive.name, timestamp=timestamp)

    def test_http_version_history_icons_and_update(self):
        entries = dict(self.entries)
        entries.pop('resources/icon.png')  # Pre-icon release fixture.
        manifest = json.loads(entries['plugins/plugin.json'])
        manifest['version'] = '0.4.6'
        entries['plugins/plugin.json'] = json_bytes(manifest)
        entries['plugins/plugin/backport_core.py'] = entries['plugins/plugin/backport_core.py'].replace(
            ("VERSION = '" + self.version + "'").encode(), b"VERSION = '0.4.6'")
        metadata = json.loads(entries['metadata.json'])
        metadata['versions'][0].update(version='0.4.6', install_size=sum(
            len(data) for name, data in entries.items() if name.startswith('plugins/')))
        entries['metadata.json'] = json_bytes(metadata)
        old = self.directory / 'previous.zip'
        old.write_bytes(zip_bytes(entries))
        old_bytes = old.read_bytes()
        self.publish(old)
        before = json.loads(fetch(self.repository_url))
        self.publish(timestamp=1788746401)
        after = json.loads(fetch(self.repository_url))
        self.assertGreater(after['packages']['update_timestamp'], before['packages']['update_timestamp'])
        self.assertEqual([self.version, '0.4.6'], verify_repository(self.repository_url))
        # Clients holding the previous root still have a valid immutable index and ZIP.
        self.assertEqual(hashlib.sha256(fetch(before['packages']['url'])).hexdigest(), before['packages']['sha256'])
        self.assertEqual(old_bytes, fetch(self.base_url + '/previous.zip'))
        self.assertEqual(old_bytes, old.read_bytes())

    def test_http_rejects_corrupt_or_missing_assets(self):
        path = self.publish()
        root = json.loads(path.read_bytes())
        self.assertEqual([self.version], verify_repository(self.repository_url))
        resource_path = path.parent / root['resources']['url'].rsplit('/', 1)[1]
        original = resource_path.read_bytes()
        resource_path.write_bytes(b'corrupt resource')
        with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
            verify_repository(self.repository_url)
        resource_path.write_bytes(original)
        self.archive.write_bytes(b'corrupt release')
        with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
            verify_repository(self.repository_url)
        with self.assertRaises(HTTPError):
            verify_repository(self.base_url + '/missing/repository.json')

    def test_http_rejects_github_style_html_page(self):
        (self.directory / 'repository.html').write_text('<html>Not a PCM JSON index</html>', encoding='utf-8')
        with self.assertRaises(ValueError):
            verify_repository(self.base_url + '/repository.html')


if __name__ == '__main__':
    unittest.main()
