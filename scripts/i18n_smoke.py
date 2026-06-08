# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import shutil
import sys
import tempfile
import types


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _write_kicad5_config(appdata):
    config_dir = os.path.join(appdata, 'kicad')
    if not os.path.isdir(config_dir):
        os.makedirs(config_dir)
    config_path = os.path.join(config_dir, 'kicad_common')
    with open(config_path, 'wb') as handle:
        handle.write(b'[common]\nLanguageID=Chinese simplified\n')
    return config_path


def _set_clean_language_env(appdata):
    saved = {}
    keys = (
        'APPDATA',
        'KICAD_BACKPORT_LANGUAGE',
        'KICAD_BACKPORT_KICAD_CONFIG_PATH',
        'KICAD_CONFIG_HOME',
        'KICAD_CONFIG_PATH',
        'KICAD_UI_LANGUAGE',
        'KICAD_LANGUAGE',
        'LANGUAGE',
        'LC_ALL',
        'LC_MESSAGES',
        'LANG',
    )
    for key in keys:
        saved[key] = os.environ.get(key)
        if key in os.environ:
            del os.environ[key]
    os.environ['APPDATA'] = appdata
    os.environ['KICAD_BACKPORT_KICAD_VERSION'] = '5.0'
    return saved


def _restore_env(saved):
    for key, value in saved.items():
        if value is None:
            if key in os.environ:
                del os.environ[key]
        else:
            os.environ[key] = value


def _check_plugin_i18n(appdata, config_path):
    if sys.version_info[0] < 3:
        return
    sys.path.insert(0, os.path.join(ROOT, 'plugin'))
    import i18n

    candidates = [str(path) for path in i18n.kicad_common_candidates()]
    assert config_path.lower() in [path.lower() for path in candidates]
    assert i18n.normalize_language('2052') == 'zh_CN'
    assert i18n.normalize_language('1036') == 'fr'
    assert i18n.detect_language() == 'zh_CN'
    assert i18n.translate('convert_button') == '转换'


def _check_legacy_action():
    if sys.version_info[0] < 3:
        pcbnew = types.ModuleType('pcbnew')

        class ActionPlugin(object):
            def register(self):
                return None

        pcbnew.ActionPlugin = ActionPlugin
        sys.modules['pcbnew'] = pcbnew
    sys.path.insert(0, ROOT)
    import legacy.kicad_backport_action as action

    assert action.detect_language() == 'zh_CN'


def main():
    work = tempfile.mkdtemp(prefix='kicad_backport_i18n_')
    try:
        appdata = os.path.join(work, 'AppData', 'Roaming')
        config_path = _write_kicad5_config(appdata)
        saved = _set_clean_language_env(appdata)
        try:
            _check_plugin_i18n(appdata, config_path)
            _check_legacy_action()
        finally:
            _restore_env(saved)
        print('i18n smoke ok')
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == '__main__':
    raise SystemExit(main())
