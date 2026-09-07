"""Optional Windows native runtime/schema smoke; never touches user settings.

Usage: python scripts/pcm_native_smoke.py --kicad-root D:/KiCad
Does not automate PCM dialogs or claim an online repository installation test.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from package_plugin import build_archive

PROBE = r'''
import importlib, os, sys
import wx
app = wx.App(False)
wx.DisableAsserts()
import pcbnew
sys.path.insert(0, sys.argv[1])
registered = []
original = pcbnew.ActionPlugin.register
def register(self):
    original(self)
    registered.append(self)
pcbnew.ActionPlugin.register = register
importlib.import_module(sys.argv[2])
assert len(registered) == int(sys.argv[3]), len(registered)
sys.path.insert(0, os.path.join(sys.argv[1], sys.argv[2], 'plugin'))
import backport_core, plugin
print(pcbnew.GetBuildVersion(), 'registered=' + str(len(registered)), 'version=' + backport_core.VERSION)
'''


def main():
    from jsonschema import Draft7Validator
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kicad-root', required=True, type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='Backport-native-') as temp:
        base = Path(temp)
        archive_path = build_archive(output_path=base/'release.zip')
        with ZipFile(archive_path) as archive:
            metadata = json.loads(archive.read('metadata.json'))
            manifest = json.loads(archive.read('plugins/plugin.json'))
            package = base/'plugins'/metadata['identifier'].replace('.', '_')
            for name in archive.namelist():
                if name.startswith('plugins/'):
                    path = package/name[8:]
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(archive.read(name))
        for version in ('6.0', '7.0', '8.0', '9.0', '10.0', '10.99'):
            install = args.kicad_root/version
            for filename in ('pcm.v1.schema.json', 'pcm.v2.schema.json', 'api.v1.schema.json'):
                schema = install/'share/kicad/schemas'/filename
                if schema.exists():
                    Draft7Validator(json.loads(schema.read_text(encoding='utf-8'))).validate(
                        manifest if filename.startswith('api.') else metadata)
                    print(version, filename, 'OK')
            python = install/'bin/python.exe'
            if not python.exists():
                print(version, 'SKIP embedded runtime: no python.exe (IPC-only host)')
                continue
            for api in (False, True):
                config = base/'config'/version
                config.mkdir(parents=True, exist_ok=True)
                (config/'kicad_common.json').write_text(json.dumps({'api': {'enable_server': api}}), encoding='utf-8')
                env = os.environ.copy()
                env.update(KICAD_CONFIG_HOME=str(base/'config'), KICAD_BACKPORT_LANGUAGE='en')
                for key in ('PYTHONHOME', 'PYTHONPATH'):
                    env.pop(key, None)
                expected = 0 if api and int(version.split('.')[0]) >= 9 else 1
                result = subprocess.run([str(python), '-B', '-u', '-c', PROBE, str(package.parent), package.name, str(expected)],
                                        env=env, cwd=base, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=30)
                if result.returncode:
                    raise RuntimeError(version + '\n' + result.stdout + result.stderr)
                print('API=' + str(api), result.stdout.strip())
    print('Native PCM runtime/schema smoke OK; GUI/online installation not exercised')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
