# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import json
import io
import shutil
import sys
import tempfile
import types

try:
    import builtins
except ImportError:
    import __builtin__ as builtins


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _write_kicad5_config(appdata):
    config_dir = os.path.join(appdata, 'kicad')
    if not os.path.isdir(config_dir):
        os.makedirs(config_dir)
    config_path = os.path.join(config_dir, 'kicad_common')
    with open(config_path, 'wb') as handle:
        handle.write(b'[common]\nLanguageID=Chinese simplified\n')
    return config_path


def _write_kicad6_config(appdata):
    config_dir = os.path.join(appdata, 'kicad')
    version_dir = os.path.join(config_dir, '6.0')
    if not os.path.isdir(version_dir):
        os.makedirs(version_dir)
    stale_path = os.path.join(config_dir, 'kicad_common')
    with open(stale_path, 'wb') as handle:
        handle.write(b'[common]\nLanguageID=English\n')
    config_path = os.path.join(version_dir, 'kicad_common.json')
    with io.open(config_path, 'w', encoding='utf-8') as handle:
        text = json.dumps({'system': {'language': 'Simplified Chinese'}})
        if sys.version_info[0] < 3:
            text = text.decode('ascii')
        handle.write(text)
    return config_path, stale_path


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
    from pathlib import Path
    sys.path.insert(0, os.path.join(ROOT, 'plugin'))
    import i18n

    candidates = [str(path) for path in i18n.kicad_common_candidates()]
    assert config_path.lower() in [path.lower() for path in candidates]
    assert i18n.normalize_language('2052') == 'zh_CN'
    assert i18n.normalize_language('1036') == 'fr'
    assert i18n.normalize_language('zh-Hans-CN') == 'zh_CN'
    assert i18n.normalize_language('zh-Hant-TW') == 'zh_TW'
    assert i18n.detect_language() == 'zh_CN'
    assert i18n.translate('convert_button') == '转换'
    win_bases = [str(path).replace('\\', '/') for path in i18n.kicad_platform_config_bases(Path('/home/user'), 'windows', 'C:/Users/user/AppData/Roaming', None)]
    linux_bases = [str(path).replace('\\', '/') for path in i18n.kicad_platform_config_bases(Path('/home/user'), 'linux', None, '/tmp/xdg')]
    mac_bases = [str(path).replace('\\', '/') for path in i18n.kicad_platform_config_bases(Path('/Users/user'), 'darwin', None, None)]
    assert 'C:/Users/user/AppData/Roaming/kicad' in win_bases
    assert 'C:/Users/user/AppData/Roaming/KiCad' in win_bases
    assert '/tmp/xdg/kicad' in linux_bases
    assert '/tmp/xdg/KiCad' in linux_bases
    assert '/Users/user/Library/Preferences/kicad' in mac_bases
    assert '/Users/user/Library/Application Support/KiCad' in mac_bases


def _check_plugin_i18n_versioned_config(appdata, config_path, stale_path):
    if sys.version_info[0] < 3:
        return
    sys.path.insert(0, os.path.join(ROOT, 'plugin'))
    import i18n

    os.environ['KICAD_BACKPORT_KICAD_VERSION'] = '6.0'
    os.environ['KICAD_BACKPORT_KICAD_CONFIG_PATH'] = os.path.join(appdata, 'kicad')
    candidates = [str(path) for path in i18n.kicad_common_candidates()]
    lowered = [path.lower() for path in candidates]
    assert config_path.lower() in lowered
    assert stale_path.lower() in lowered
    assert lowered.index(config_path.lower()) < lowered.index(stale_path.lower())
    assert i18n.detect_language() == 'zh_CN'
    assert i18n.translate('convert_button') == '转换'


def _check_legacy_action():
    previous = sys.modules.get('pcbnew')
    pcbnew = types.ModuleType('pcbnew')

    class ActionPlugin(object):
        def register(self):
            return None

    pcbnew.ActionPlugin = ActionPlugin
    sys.modules['pcbnew'] = pcbnew
    try:
        sys.path.insert(0, ROOT)
        import legacy.kicad_backport_action as action

        assert action.detect_language() == 'zh_CN'
    finally:
        if previous is None:
            sys.modules.pop('pcbnew', None)
        else:
            sys.modules['pcbnew'] = previous


def _check_legacy_fallback_translations():
    previous_pcbnew = sys.modules.get('pcbnew')
    previous_i18n = sys.modules.get('i18n')
    previous_action = sys.modules.get('legacy.kicad_backport_action')
    pcbnew = types.ModuleType('pcbnew')

    class ActionPlugin(object):
        def register(self):
            return None

    pcbnew.ActionPlugin = ActionPlugin
    sys.modules['pcbnew'] = pcbnew
    sys.modules.pop('i18n', None)
    sys.modules.pop('legacy.kicad_backport_action', None)
    original_import = builtins.__import__

    def blocked_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == 'i18n':
            raise ImportError('forced i18n import failure')
        return original_import(name, globals, locals, fromlist, level)

    builtins.__import__ = blocked_import
    try:
        sys.path.insert(0, ROOT)
        import legacy.kicad_backport_action as action

        assert action.detect_language() == 'zh_CN'
        assert action._normalize_language(u'简体中文') == 'zh_CN'
        assert action._normalize_language(u'繁體中文') == 'zh_TW'
        assert action._normalize_language('zh-Hans-CN') == 'zh_CN'
        assert action._normalize_language('zh-Hant-TW') == 'zh_TW'
        win_bases = [path.replace('\\', '/') for path in action._platform_config_bases('/home/user', 'windows', 'C:/Users/user/AppData/Roaming', None)]
        linux_bases = [path.replace('\\', '/') for path in action._platform_config_bases('/home/user', 'linux', None, '/tmp/xdg')]
        mac_bases = [path.replace('\\', '/') for path in action._platform_config_bases('/Users/user', 'darwin', None, None)]
        assert 'C:/Users/user/AppData/Roaming/kicad' in win_bases
        assert 'C:/Users/user/AppData/Roaming/KiCad' in win_bases
        assert '/tmp/xdg/kicad' in linux_bases
        assert '/tmp/xdg/KiCad' in linux_bases
        assert '/Users/user/Library/Preferences/kicad' in mac_bases
        assert '/Users/user/Library/Application Support/KiCad' in mac_bases
        assert action.translate('action_name', 'zh_CN') == u'创建 KiCad 兼容副本'
        assert action.translate('action_description', 'zh_CN') == u'创建可供旧版 KiCad 打开的工程或文件副本。'
        assert action.translate('action_name', 'zh_TW') == u'建立 KiCad 相容副本'
    finally:
        builtins.__import__ = original_import
        if previous_pcbnew is None:
            sys.modules.pop('pcbnew', None)
        else:
            sys.modules['pcbnew'] = previous_pcbnew
        if previous_i18n is None:
            sys.modules.pop('i18n', None)
        else:
            sys.modules['i18n'] = previous_i18n
        if previous_action is None:
            sys.modules.pop('legacy.kicad_backport_action', None)
        else:
            sys.modules['legacy.kicad_backport_action'] = previous_action


def main():
    work = tempfile.mkdtemp(prefix='kicad_backport_i18n_')
    try:
        appdata = os.path.join(work, 'AppData', 'Roaming')
        config_path = _write_kicad5_config(appdata)
        saved = _set_clean_language_env(appdata)
        try:
            _check_plugin_i18n(appdata, config_path)
            _check_legacy_action()
            _check_legacy_fallback_translations()
            config6_path, stale_path = _write_kicad6_config(appdata)
            _check_plugin_i18n_versioned_config(appdata, config6_path, stale_path)
        finally:
            _restore_env(saved)
        print('i18n smoke ok')
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == '__main__':
    raise SystemExit(main())
