# -*- coding: utf-8 -*-
import locale
import json
import os
import platform
import re
import subprocess
import sys
try:
    import pcbnew
except Exception:
    pcbnew = None
try:
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.join(_root, 'plugin'))
    from i18n import detect_language, translate
except Exception:
    _LANGUAGE_LABELS = {
        'english': 'en',
        'american english': 'en',
        'en': 'en',
        'en_us': 'en',
        '1033': 'en',
        u'中文': 'zh_CN',
        u'中文 (中国)': 'zh_CN',
        u'中文 (简体)': 'zh_CN',
        u'中文（简体）': 'zh_CN',
        u'简体': 'zh_CN',
        u'简体中文': 'zh_CN',
        u'简体中文 (中国)': 'zh_CN',
        u'简体中文（中国）': 'zh_CN',
        'chinese simplified': 'zh_CN',
        'simplified chinese': 'zh_CN',
        'chinese (simplified)': 'zh_CN',
        'chinese_simplified': 'zh_CN',
        '2052': 'zh_CN',
        u'中文 (台灣)': 'zh_TW',
        u'中文（繁體）': 'zh_TW',
        u'中文 (繁體)': 'zh_TW',
        u'繁體': 'zh_TW',
        u'繁體中文': 'zh_TW',
        u'繁體中文 (台灣)': 'zh_TW',
        u'繁體中文（台灣）': 'zh_TW',
        u'繁体中文': 'zh_TW',
        u'繁体中文 (台湾)': 'zh_TW',
        u'繁体中文（台湾）': 'zh_TW',
        'chinese traditional': 'zh_TW',
        'traditional chinese': 'zh_TW',
        'chinese (traditional)': 'zh_TW',
        'chinese_traditional': 'zh_TW',
        '1028': 'zh_TW',
        'francais': 'fr',
        'french': 'fr',
        'fr': 'fr',
        '1036': 'fr',
        'deutsch': 'de',
        'german': 'de',
        'de': 'de',
        '1031': 'de',
        'italiano': 'it',
        'italian': 'it',
        'it': 'it',
        '1040': 'it',
    }

    _MESSAGES = {
        'en': {
            'action_name': 'Create KiCad Backport',
            'action_category': 'KiCad Backport',
            'action_description': 'Create a compatibility copy of a KiCad project or file.',
        },
        'zh_CN': {
            'action_name': u'创建 KiCad 兼容副本',
            'action_category': 'KiCad Backport',
            'action_description': u'创建可供旧版 KiCad 打开的工程或文件副本。',
        },
        'zh_TW': {
            'action_name': u'建立 KiCad 相容副本',
            'action_category': 'KiCad Backport',
            'action_description': u'建立可供舊版 KiCad 開啟的工程或檔案副本。',
        },
        'fr': {
            'action_name': 'Creer un backport KiCad',
            'action_category': 'KiCad Backport',
            'action_description': "Creer une copie compatible d'un projet ou fichier KiCad.",
        },
        'de': {
            'action_name': 'KiCad-Backport erstellen',
            'action_category': 'KiCad Backport',
            'action_description': 'Erstellt eine kompatible Kopie eines KiCad-Projekts oder einer Datei.',
        },
        'it': {
            'action_name': 'Crea backport KiCad',
            'action_category': 'KiCad Backport',
            'action_description': 'Crea una copia compatibile di un progetto o file KiCad.',
        },
    }

    def _normalize_language(value):
        if not value:
            return None
        try:
            raw = value.strip()
        except Exception:
            raw = str(value).strip()
        if not raw or raw.lower() == 'default':
            return None
        lowered = raw.lower().replace('-', '_')
        if lowered in _LANGUAGE_LABELS:
            return _LANGUAGE_LABELS[lowered]
        if lowered.startswith('zh_hans') or lowered.startswith('zh_cn') or lowered.startswith('zh_sg') or 'simplified' in lowered:
            return 'zh_CN'
        if lowered.startswith('zh_hant') or lowered.startswith('zh_tw') or lowered.startswith('zh_hk') or lowered.startswith('zh_mo') or 'traditional' in lowered:
            return 'zh_TW'
        if lowered.startswith('zh'):
            return 'zh_CN'
        if lowered.startswith('fr'):
            return 'fr'
        if lowered.startswith('de'):
            return 'de'
        if lowered.startswith('it'):
            return 'it'
        if lowered.startswith('en'):
            return 'en'
        return None

    def _common_config_files(base):
        names = ('kicad_common', 'kicad_common.json', 'kicad', 'kicad.json', 'pcbnew', 'pcbnew.json', 'eeschema', 'eeschema.json')
        if not base:
            return
        if os.path.isfile(base):
            yield base
            return
        for name in names:
            path = os.path.join(base, name)
            if os.path.exists(path):
                yield path
        if not os.path.isdir(base):
            return
        try:
            children = os.listdir(base)
        except Exception:
            return
        for child in children:
            child_path = os.path.join(base, child)
            if not os.path.isdir(child_path):
                continue
            for name in names:
                path = os.path.join(child_path, name)
                if os.path.exists(path):
                    yield path

    def _runtime_versions():
        seen = set()

        def emit(value):
            if not value:
                return
            match = re.search('(\\d+)\\.(\\d+)', str(value))
            if not match:
                return
            major_minor = '{0}.{1}'.format(match.group(1), match.group(2))
            if major_minor not in seen:
                seen.add(major_minor)
                yield major_minor
            major = match.group(1)
            if major not in seen:
                seen.add(major)
                yield major

        if pcbnew is not None:
            for attr in ('GetMajorMinorVersion', 'GetBuildVersion', 'GetKicadConfigPath'):
                getter = getattr(pcbnew, attr, None)
                if callable(getter):
                    try:
                        value = getter()
                    except Exception:
                        value = ''
                    for version in emit(value):
                        yield version
        for key in ('KICAD_BACKPORT_KICAD_VERSION', 'KICAD_BACKPORT_KICAD_BUILD_VERSION', 'KICAD_BACKPORT_KICAD_CONFIG_PATH'):
            for version in emit(os.environ.get(key)):
                yield version

    def _common_config_files_for_base(base, versions):
        if not base:
            return
        if os.path.isfile(base):
            yield base
            return
        for version in versions:
            for path in _common_config_files(os.path.join(base, version)):
                yield path
        for path in _common_config_files(base):
            yield path

    def _platform_config_bases(home, system, appdata=None, xdg_config_home=None):
        system = (system or '').lower()
        if system == 'windows':
            if appdata:
                yield os.path.join(appdata, 'kicad')
                yield os.path.join(appdata, 'KiCad')
        elif system == 'darwin':
            yield os.path.join(home, 'Library', 'Preferences', 'kicad')
            yield os.path.join(home, 'Library', 'Preferences', 'KiCad')
            yield os.path.join(home, 'Library', 'Application Support', 'kicad')
            yield os.path.join(home, 'Library', 'Application Support', 'KiCad')
        else:
            config_home = xdg_config_home or os.path.join(home, '.config')
            yield os.path.join(config_home, 'kicad')
            yield os.path.join(config_home, 'KiCad')

    def _kicad_config_files():
        bases = []
        for key in ('KICAD_BACKPORT_KICAD_CONFIG_PATH', 'KICAD_CONFIG_HOME', 'KICAD_CONFIG_PATH'):
            value = os.environ.get(key)
            if value:
                bases.append(value)
                if os.path.basename(value) in ('kicad_common', 'kicad_common.json'):
                    bases.append(os.path.dirname(value))
        if pcbnew is not None:
            getter = getattr(pcbnew, 'GetKicadConfigPath', None)
            if callable(getter):
                try:
                    value = getter()
                except Exception:
                    value = ''
                if value:
                    bases.append(value)
        bases.extend(_platform_config_bases(os.path.expanduser('~'), platform.system(), os.environ.get('APPDATA'), os.environ.get('XDG_CONFIG_HOME')))
        seen = set()
        versions = list(_runtime_versions())
        for base in bases:
            for path in _common_config_files_for_base(base, versions):
                key = path.lower()
                if key in seen:
                    continue
                seen.add(key)
                yield path

    def _find_language_value(value):
        if isinstance(value, dict):
            system = value.get('system')
            if isinstance(system, dict):
                language = system.get('language')
                if language:
                    return str(language)
            for key, child in value.items():
                if str(key).lower() == 'language' and child:
                    return str(child)
                found = _find_language_value(child)
                if found:
                    return found
        elif isinstance(value, list):
            for child in value:
                found = _find_language_value(child)
                if found:
                    return found
        return None

    def _config_languages(text):
        try:
            payload = json.loads(text)
            language = _find_language_value(payload)
            if language:
                yield language
                return
        except Exception:
            pass
        for language in _legacy_config_languages(text):
            yield language

    def _legacy_config_languages(text):
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith(('#', ';')):
                continue
            match = re.match('(?i)^(?:system[./\\\\])?(?:language|languageid|language_id|languagecode|language_code|locale)\\s*[:=]\\s*(.+)$', line)
            if match:
                yield match.group(1).strip().strip('"\'')

    def _system_locale_values():
        for getter in (lambda: locale.getlocale()[0], lambda: locale.getdefaultlocale()[0]):
            try:
                value = getter()
            except Exception:
                value = None
            if value:
                yield value
        system = platform.system().lower()
        if system == 'windows':
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                for getter_name in ('GetUserDefaultLocaleName', 'GetSystemDefaultLocaleName'):
                    getter = getattr(kernel32, getter_name, None)
                    if getter is None:
                        continue
                    buffer = ctypes.create_unicode_buffer(85)
                    if getter(buffer, len(buffer)):
                        yield buffer.value
            except Exception:
                pass
            try:
                import ctypes
                lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
                value = {
                    1033: 'en_US',
                    2052: 'zh_CN',
                    1028: 'zh_TW',
                    1036: 'fr_FR',
                    1031: 'de_DE',
                    1040: 'it_IT',
                }.get(lang_id)
            except Exception:
                value = None
            if value:
                yield value
        elif system == 'darwin':
            for value in _macos_locale_values():
                yield value

    def _macos_locale_values():
        commands = (
            ('defaults', 'read', '-g', 'AppleLocale'),
            ('defaults', 'read', '-g', 'AppleLanguages'),
        )
        for command in commands:
            try:
                proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                output, _stderr = proc.communicate()
            except Exception:
                continue
            if proc.returncode != 0:
                continue
            try:
                text = output.decode('utf-8', 'replace')
            except Exception:
                text = str(output)
            for value in re.findall(r'"([^"]+)"', text):
                if value:
                    yield value
            for line in text.splitlines():
                value = line.strip().strip('(),;"')
                if value and not value.startswith('('):
                    yield value

    def detect_language():
        values = []
        value = os.environ.get('KICAD_BACKPORT_LANGUAGE')
        if value:
            values.append(value)
        for path in _kicad_config_files():
            try:
                with open(path, 'rb') as handle:
                    text = handle.read().decode('utf-8', 'replace')
            except Exception:
                continue
            values.extend(_config_languages(text))
        for key in ('KICAD_UI_LANGUAGE', 'KICAD_LANGUAGE', 'LANGUAGE', 'LC_ALL', 'LC_MESSAGES', 'LANG'):
            value = os.environ.get(key)
            if value:
                values.append(value)
        values.extend(_system_locale_values())
        for value in values:
            lang = _normalize_language(value)
            if lang:
                return lang
        return 'en'

    def translate(key, language=None):
        lang = language or detect_language()
        table = _MESSAGES.get(lang, _MESSAGES['en'])
        return table.get(key, _MESSAGES['en'].get(key, key))

def plugin_root():
    here = os.path.abspath(__file__)
    parent = os.path.dirname(here)
    if os.path.basename(parent) == 'legacy':
        return os.path.dirname(parent)
    return parent

def _python3_candidates():
    env = os.environ.get('KICAD_BACKPORT_PYTHON', '').strip()
    if env:
        yield [env]
    if os.name == 'nt':
        yield ['pyw', '-3']
        yield ['pythonw']
        yield ['py', '-3']
    yield ['python3']
    yield ['python']

def _launch_external_python3(launcher):
    last_error = None
    for command in _python3_candidates():
        try:
            kwargs = {}
            env = os.environ.copy()
            env.setdefault('KICAD_BACKPORT_LEGACY', '1')
            env.setdefault('KICAD_BACKPORT_GUI_BACKEND', 'tk,wx')
            env.setdefault('KICAD_BACKPORT_LANGUAGE', detect_language())
            if pcbnew is not None:
                for attr, key in (
                    ('GetMajorMinorVersion', 'KICAD_BACKPORT_KICAD_VERSION'),
                    ('GetBuildVersion', 'KICAD_BACKPORT_KICAD_BUILD_VERSION'),
                    ('GetKicadConfigPath', 'KICAD_BACKPORT_KICAD_CONFIG_PATH'),
                ):
                    getter = getattr(pcbnew, attr, None)
                    if callable(getter):
                        try:
                            value = getter()
                        except Exception:
                            value = ''
                        if value:
                            env.setdefault(key, str(value))
            kwargs['env'] = env
            if os.name == 'nt':
                flags = 0
                flags |= getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)
                flags |= getattr(subprocess, 'DETACHED_PROCESS', 0)
                flags |= getattr(subprocess, 'CREATE_NO_WINDOW', 0)
                if flags:
                    kwargs['creationflags'] = flags
            subprocess.Popen(command + [launcher], **kwargs)
            return 0
        except Exception as exc:
            last_error = exc
    if last_error is not None:
        raise RuntimeError('Unable to launch external Python 3: {0}'.format(last_error))
    raise RuntimeError('Unable to launch external Python 3')

def _launch_in_process(launcher):
    import importlib.util
    sys.path.insert(0, os.path.dirname(launcher))
    spec = importlib.util.spec_from_file_location('kicad_backport_gui', launcher)
    if spec is None or spec.loader is None:
        raise RuntimeError('Unable to load plugin/plugin.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    result = module.run_gui()
    return 0 if result is None else result

def launch_gui():
    root = plugin_root()
    launcher = os.path.join(root, 'plugin', 'plugin.py')
    if not os.path.exists(launcher):
        raise RuntimeError('plugin/plugin.py was not found')
    if sys.version_info[0] < 3:
        result = _launch_external_python3(launcher)
    else:
        result = _launch_in_process(launcher)
    if result not in (None, 0):
        raise RuntimeError('KiCad Backport exited with code {0}'.format(result))
if pcbnew is not None:

    class KiCadBackportAction(pcbnew.ActionPlugin):

        def defaults(self):
            lang = detect_language()
            self.name = translate('action_name', lang)
            self.category = translate('action_category', lang)
            self.description = translate('action_description', lang)
            self.show_toolbar_button = True
            icon = os.path.join(plugin_root(), 'assets', 'icons', 'backport-light-32.png')
            if os.path.exists(icon):
                self.icon_file_name = icon

        def Run(self):
            launch_gui()
    KiCadBackportAction().register()
