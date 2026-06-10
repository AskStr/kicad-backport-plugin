import json
import locale
import os
import platform
import re
import subprocess
import sys
import ctypes
from pathlib import Path
from typing import Dict, Iterable, Optional
MESSAGES = {'en': {'app_title': 'KiCad Backport', 'action_name': 'Create KiCad Backport', 'action_category': 'KiCad Backport', 'action_description': 'Create a compatibility copy of a KiCad project or file.', 'input_label': 'Input file or project', 'mode_label': 'Conversion scope', 'mode_project': 'Whole project', 'mode_pcb': 'PCB only', 'mode_sch': 'Schematic only', 'output_label': 'Output file or folder', 'file_button': 'File', 'folder_button': 'Folder', 'save_as_button': 'Save As', 'target_label': 'Target KiCad version', 'target_6_0': 'KiCad 6.0', 'target_5_1': 'KiCad 5.1', 'target_5_0': 'KiCad 5.0', 'convert_button': 'Convert', 'open_output_button': 'Open Output Folder', 'open_output_error': 'Unable to open output folder:\n{detail}', 'initial_status': 'Select an input and output path.', 'converting_status': 'Converting...', 'failed_status': 'Conversion failed.', 'complete_status': 'Conversion complete.', 'missing_paths': 'Input and output paths are required.', 'same_path_error': 'The output path must be different from the input path.', 'overwrite_confirm': 'The output path already exists. Continue? Related KiCad project files will be overwritten; other files will be kept.', 'complete_message': 'Conversion complete.', 'complete_detail': 'Output:\n{output}', 'warnings_summary': '{count} warning(s). Details were saved to:\n{report}', 'error_output_dir_same': 'The output folder must be different from the input folder.', 'error_output_dir_inside_input': 'The output folder cannot be inside the input folder.', 'error_output_dir_exists': 'The output folder already exists. Please retry with the current plugin version.', 'error_output_file_same': 'The output file must be different from the input file.', 'error_input_missing': 'The input path does not exist.', 'error_permission': 'Permission denied. Please choose a writable output folder.', 'error_cli_missing': 'The converter executable was not found or could not be started.', 'error_target_required': 'Please choose a target KiCad version.', 'error_paths_required': 'Input and output paths are required.', 'error_invalid_kicad_file': 'The selected file is not a supported KiCad source file.', 'error_conversion_failed': 'Conversion failed:\n{detail}', 'warnings_title': 'Warnings:', 'kicad_files': 'KiCad files', 'all_files': 'All files', 'wx_missing': 'wxPython is not available; run plugin.py with --input and --output instead.', 'cli_description': 'KiCad Backport plugin launcher', 'cli_paths_required': '--input and --output are required in command-line mode', 'copyright': 'askstar', 'version_label': 'Version: {version}'}, 'zh_CN': {'app_title': 'KiCad Backport', 'action_name': '创建 KiCad 兼容副本', 'action_category': 'KiCad Backport', 'action_description': '创建可供旧版 KiCad 打开的工程或文件副本。', 'input_label': '输入文件或工程', 'mode_label': '转换范围', 'mode_project': '整个工程', 'mode_pcb': '仅 PCB', 'mode_sch': '仅 SCH', 'output_label': '输出文件或文件夹', 'file_button': '文件', 'folder_button': '文件夹', 'save_as_button': '另存为', 'target_label': '目标 KiCad 版本', 'target_6_0': 'KiCad 6.0', 'target_5_1': 'KiCad 5.1', 'target_5_0': 'KiCad 5.0', 'convert_button': '转换', 'open_output_button': '打开输出文件夹', 'open_output_error': '无法打开输出文件夹：\n{detail}', 'initial_status': '请选择输入和输出路径。', 'converting_status': '正在转换...', 'failed_status': '转换失败。', 'complete_status': '转换完成。', 'missing_paths': '必须选择输入和输出路径。', 'same_path_error': '输出路径必须和输入路径不同。', 'overwrite_confirm': '输出路径已存在。是否继续？将覆盖相关 KiCad 工程文件，其它文件会保留。', 'complete_message': '转换已成功完成。', 'complete_detail': '输出位置：\n{output}', 'warnings_summary': '有 {count} 条兼容性提示，不影响输出文件生成。详细信息已保存到：\n{report}', 'error_output_dir_same': '输出文件夹必须和输入文件夹不同。', 'error_output_dir_inside_input': '输出文件夹不能位于输入文件夹内部。', 'error_output_dir_exists': '输出文件夹已存在。请使用当前插件版本重试。', 'error_output_file_same': '输出文件必须和输入文件不同。', 'error_input_missing': '输入路径不存在。', 'error_permission': '没有写入权限。请选择可写入的输出文件夹。', 'error_cli_missing': '未找到或无法启动转换程序。', 'error_target_required': '请选择目标 KiCad 版本。', 'error_paths_required': '必须选择输入和输出路径。', 'error_invalid_kicad_file': '所选文件不是受支持的 KiCad 源文件。', 'error_conversion_failed': '转换失败：\n{detail}', 'warnings_title': '警告：', 'kicad_files': 'KiCad 文件', 'all_files': '所有文件', 'wx_missing': '当前 Python 环境没有 wxPython；请使用 --input 和 --output 参数运行 plugin.py。', 'cli_description': 'KiCad 降级转换插件启动器', 'cli_paths_required': '命令行模式必须提供 --input 和 --output', 'copyright': '问星', 'version_label': '版本：{version}'}, 'zh_TW': {'app_title': 'KiCad Backport', 'action_name': '建立 KiCad 相容副本', 'action_category': 'KiCad Backport', 'action_description': '建立可供舊版 KiCad 開啟的工程或檔案副本。', 'input_label': '輸入檔案或工程', 'mode_label': '轉換範圍', 'mode_project': '整個工程', 'mode_pcb': '僅 PCB', 'mode_sch': '僅 SCH', 'output_label': '輸出檔案或資料夾', 'file_button': '檔案', 'folder_button': '資料夾', 'save_as_button': '另存為', 'target_label': '目標 KiCad 版本', 'target_6_0': 'KiCad 6.0', 'target_5_1': 'KiCad 5.1', 'target_5_0': 'KiCad 5.0', 'convert_button': '轉換', 'open_output_button': '開啟輸出資料夾', 'open_output_error': '無法開啟輸出資料夾：\n{detail}', 'initial_status': '請選擇輸入和輸出路徑。', 'converting_status': '正在轉換...', 'failed_status': '轉換失敗。', 'complete_status': '轉換完成。', 'missing_paths': '必須選擇輸入和輸出路徑。', 'same_path_error': '輸出路徑必須和輸入路徑不同。', 'overwrite_confirm': '輸出路徑已存在。是否繼續？將覆蓋相關 KiCad 工程檔案，其它檔案會保留。', 'complete_message': '轉換已成功完成。', 'complete_detail': '輸出位置：\n{output}', 'warnings_summary': '有 {count} 條相容性提示，不影響輸出檔案產生。詳細資訊已儲存到：\n{report}', 'error_output_dir_same': '輸出資料夾必須和輸入資料夾不同。', 'error_output_dir_inside_input': '輸出資料夾不能位於輸入資料夾內部。', 'error_output_dir_exists': '輸出資料夾已存在。請使用目前外掛版本重試。', 'error_output_file_same': '輸出檔案必須和輸入檔案不同。', 'error_input_missing': '輸入路徑不存在。', 'error_permission': '沒有寫入權限。請選擇可寫入的輸出資料夾。', 'error_cli_missing': '找不到或無法啟動轉換程式。', 'error_target_required': '請選擇目標 KiCad 版本。', 'error_paths_required': '必須選擇輸入和輸出路徑。', 'error_invalid_kicad_file': '所選檔案不是支援的 KiCad 原始檔。', 'error_conversion_failed': '轉換失敗：\n{detail}', 'warnings_title': '警告：', 'kicad_files': 'KiCad 檔案', 'all_files': '所有檔案', 'wx_missing': '目前 Python 環境沒有 wxPython；請使用 --input 和 --output 參數執行 plugin.py。', 'cli_description': 'KiCad 降級轉換外掛啟動器', 'cli_paths_required': '命令列模式必須提供 --input 和 --output', 'copyright': '问星', 'version_label': '版本：{version}'}, 'fr': {'app_title': 'KiCad Backport', 'action_name': 'Creer un backport KiCad', 'action_category': 'KiCad Backport', 'action_description': "Creer une copie compatible d'un projet ou fichier KiCad.", 'input_label': 'Fichier ou projet source', 'mode_label': 'Portee de conversion', 'mode_project': 'Projet complet', 'mode_pcb': 'PCB uniquement', 'mode_sch': 'Schema uniquement', 'output_label': 'Fichier ou dossier de sortie', 'file_button': 'Fichier', 'folder_button': 'Dossier', 'save_as_button': 'Enregistrer sous', 'target_label': 'Version KiCad cible', 'target_6_0': 'KiCad 6.0', 'target_5_1': 'KiCad 5.1', 'target_5_0': 'KiCad 5.0', 'convert_button': 'Convertir', 'open_output_button': 'Ouvrir le dossier de sortie', 'open_output_error': 'Impossible d''ouvrir le dossier de sortie :\n{detail}', 'initial_status': 'Selectionnez un chemin source et un chemin de sortie.', 'converting_status': 'Conversion en cours...', 'failed_status': 'La conversion a echoue.', 'complete_status': 'Conversion terminee.', 'missing_paths': 'Les chemins source et de sortie sont obligatoires.', 'same_path_error': 'Le chemin de sortie doit etre different du chemin source.', 'overwrite_confirm': 'Le chemin de sortie existe deja. Continuer ? Les fichiers KiCad concernes seront remplaces ; les autres fichiers seront conserves.', 'complete_message': 'Conversion terminee.', 'complete_detail': 'Sortie :\n{output}', 'warnings_summary': '{count} avertissement(s). Details enregistres dans :\n{report}', 'error_output_dir_same': 'Le dossier de sortie doit etre different du dossier source.', 'error_output_dir_inside_input': 'Le dossier de sortie ne peut pas etre dans le dossier source.', 'error_output_dir_exists': 'Le dossier de sortie existe deja. Reessayez avec la version actuelle du plugin.', 'error_output_file_same': 'Le fichier de sortie doit etre different du fichier source.', 'error_input_missing': "Le chemin source n'existe pas.", 'error_permission': 'Permission refusee. Choisissez un dossier de sortie accessible en ecriture.', 'error_cli_missing': "L'executable de conversion est introuvable ou n'a pas pu demarrer.", 'error_target_required': 'Choisissez une version KiCad cible.', 'error_paths_required': 'Les chemins source et de sortie sont obligatoires.', 'error_invalid_kicad_file': "Le fichier selectionne n'est pas un fichier source KiCad pris en charge.", 'error_conversion_failed': 'La conversion a echoue :\n{detail}', 'warnings_title': 'Avertissements :', 'kicad_files': 'Fichiers KiCad', 'all_files': 'Tous les fichiers', 'wx_missing': "wxPython n'est pas disponible ; lancez plugin.py avec --input et --output.", 'cli_description': 'Lanceur du plugin de conversion KiCad', 'cli_paths_required': '--input et --output sont obligatoires en mode ligne de commande', 'copyright': 'askstar', 'version_label': 'Version : {version}'}, 'de': {'app_title': 'KiCad Backport', 'action_name': 'KiCad-Backport erstellen', 'action_category': 'KiCad Backport', 'action_description': 'Erstellt eine kompatible Kopie eines KiCad-Projekts oder einer Datei.', 'input_label': 'Eingabedatei oder Projekt', 'mode_label': 'Konvertierungsumfang', 'mode_project': 'Ganzes Projekt', 'mode_pcb': 'Nur PCB', 'mode_sch': 'Nur Schaltplan', 'output_label': 'Ausgabedatei oder Ordner', 'file_button': 'Datei', 'folder_button': 'Ordner', 'save_as_button': 'Speichern unter', 'target_label': 'Zielversion von KiCad', 'target_6_0': 'KiCad 6.0', 'target_5_1': 'KiCad 5.1', 'target_5_0': 'KiCad 5.0', 'convert_button': 'Konvertieren', 'open_output_button': 'Ausgabeordner oeffnen', 'open_output_error': 'Ausgabeordner kann nicht geoeffnet werden:\n{detail}', 'initial_status': 'Waehlen Sie Eingabe- und Ausgabepfad aus.', 'converting_status': 'Konvertierung laeuft...', 'failed_status': 'Konvertierung fehlgeschlagen.', 'complete_status': 'Konvertierung abgeschlossen.', 'missing_paths': 'Eingabe- und Ausgabepfad sind erforderlich.', 'same_path_error': 'Der Ausgabepfad muss sich vom Eingabepfad unterscheiden.', 'overwrite_confirm': 'Der Ausgabepfad existiert bereits. Fortfahren? Zugehoerige KiCad-Projektdateien werden ueberschrieben; andere Dateien bleiben erhalten.', 'complete_message': 'Konvertierung abgeschlossen.', 'complete_detail': 'Ausgabe:\n{output}', 'warnings_summary': '{count} Warnung(en). Details wurden gespeichert unter:\n{report}', 'error_output_dir_same': 'Der Ausgabeordner muss sich vom Eingabeordner unterscheiden.', 'error_output_dir_inside_input': 'Der Ausgabeordner darf nicht im Eingabeordner liegen.', 'error_output_dir_exists': 'Der Ausgabeordner existiert bereits. Bitte mit der aktuellen Plugin-Version erneut versuchen.', 'error_output_file_same': 'Die Ausgabedatei muss sich von der Eingabedatei unterscheiden.', 'error_input_missing': 'Der Eingabepfad existiert nicht.', 'error_permission': 'Zugriff verweigert. Bitte einen beschreibbaren Ausgabeordner waehlen.', 'error_cli_missing': 'Das Konvertierungsprogramm wurde nicht gefunden oder konnte nicht gestartet werden.', 'error_target_required': 'Bitte eine Zielversion von KiCad waehlen.', 'error_paths_required': 'Eingabe- und Ausgabepfad sind erforderlich.', 'error_invalid_kicad_file': 'Die ausgewaehlte Datei ist keine unterstuetzte KiCad-Quelldatei.', 'error_conversion_failed': 'Konvertierung fehlgeschlagen:\n{detail}', 'warnings_title': 'Warnungen:', 'kicad_files': 'KiCad-Dateien', 'all_files': 'Alle Dateien', 'wx_missing': 'wxPython ist nicht verfuegbar; starten Sie plugin.py mit --input und --output.', 'cli_description': 'Startprogramm fuer das kicad-backport', 'cli_paths_required': '--input und --output sind im Befehlszeilenmodus erforderlich', 'copyright': 'askstar', 'version_label': 'Version: {version}'}, 'it': {'app_title': 'KiCad Backport', 'action_name': 'Crea backport KiCad', 'action_category': 'KiCad Backport', 'action_description': 'Crea una copia compatibile di un progetto o file KiCad.', 'input_label': 'File o progetto di origine', 'mode_label': 'Ambito conversione', 'mode_project': 'Intero progetto', 'mode_pcb': 'Solo PCB', 'mode_sch': 'Solo schema', 'output_label': 'File o cartella di destinazione', 'file_button': 'File', 'folder_button': 'Cartella', 'save_as_button': 'Salva con nome', 'target_label': 'Versione KiCad di destinazione', 'target_6_0': 'KiCad 6.0', 'target_5_1': 'KiCad 5.1', 'target_5_0': 'KiCad 5.0', 'convert_button': 'Converti', 'open_output_button': 'Apri cartella destinazione', 'open_output_error': 'Impossibile aprire la cartella di destinazione:\n{detail}', 'initial_status': 'Selezionare un percorso di origine e uno di destinazione.', 'converting_status': 'Conversione in corso...', 'failed_status': 'Conversione non riuscita.', 'complete_status': 'Conversione completata.', 'missing_paths': 'I percorsi di origine e destinazione sono obbligatori.', 'same_path_error': 'Il percorso di destinazione deve essere diverso da quello di origine.', 'overwrite_confirm': 'Il percorso di destinazione esiste gia. Continuare? I file KiCad interessati saranno sovrascritti; gli altri file resteranno invariati.', 'complete_message': 'Conversione completata.', 'complete_detail': 'Destinazione:\n{output}', 'warnings_summary': '{count} avviso/i. Dettagli salvati in:\n{report}', 'error_output_dir_same': 'La cartella di destinazione deve essere diversa da quella di origine.', 'error_output_dir_inside_input': 'La cartella di destinazione non puo trovarsi dentro quella di origine.', 'error_output_dir_exists': 'La cartella di destinazione esiste gia. Riprovare con la versione corrente del plugin.', 'error_output_file_same': 'Il file di destinazione deve essere diverso da quello di origine.', 'error_input_missing': 'Il percorso di origine non esiste.', 'error_permission': 'Permesso negato. Scegliere una cartella di destinazione scrivibile.', 'error_cli_missing': "L'eseguibile di conversione non e stato trovato o non puo essere avviato.", 'error_target_required': 'Scegliere una versione KiCad di destinazione.', 'error_paths_required': 'I percorsi di origine e destinazione sono obbligatori.', 'error_invalid_kicad_file': 'Il file selezionato non e un file sorgente KiCad supportato.', 'error_conversion_failed': 'Conversione non riuscita:\n{detail}', 'warnings_title': 'Avvisi:', 'kicad_files': 'File KiCad', 'all_files': 'Tutti i file', 'wx_missing': 'wxPython non e disponibile; eseguire plugin.py con --input e --output.', 'cli_description': 'Avvio del plugin di conversione KiCad', 'cli_paths_required': '--input e --output sono obbligatori in modalita riga di comando', 'copyright': 'askstar', 'version_label': 'Versione: {version}'}}
KICAD_LANGUAGE_LABELS = {'english': 'en', 'american english': 'en', 'en_us': 'en', 'en': 'en', '1033': 'en', '中文': 'zh_CN', '中文 (中国)': 'zh_CN', '中文 (简体)': 'zh_CN', '中文（简体）': 'zh_CN', '简体': 'zh_CN', '简体中文': 'zh_CN', '简体中文 (中国)': 'zh_CN', '简体中文（中国）': 'zh_CN', '2052': 'zh_CN', '中文 (台灣)': 'zh_TW', '中文（繁體）': 'zh_TW', '中文 (繁體)': 'zh_TW', '繁體': 'zh_TW', '繁體中文': 'zh_TW', '繁體中文 (台灣)': 'zh_TW', '繁體中文（台灣）': 'zh_TW', '繁体中文': 'zh_TW', '繁体中文 (台湾)': 'zh_TW', '繁体中文（台湾）': 'zh_TW', '1028': 'zh_TW', 'chinese simplified': 'zh_CN', 'simplified chinese': 'zh_CN', 'chinese (simplified)': 'zh_CN', 'chinese_simplified': 'zh_CN', 'chinese traditional': 'zh_TW', 'traditional chinese': 'zh_TW', 'chinese (traditional)': 'zh_TW', 'chinese_traditional': 'zh_TW', 'français': 'fr', 'francais': 'fr', 'french': 'fr', 'fr': 'fr', '1036': 'fr', 'deutsch': 'de', 'german': 'de', 'de': 'de', '1031': 'de', 'italiano': 'it', 'italian': 'it', 'it': 'it', '1040': 'it'}

def translate(key, language=None):
    lang = language or detect_language()
    table = MESSAGES.get(lang, MESSAGES['en'])
    return table.get(key, MESSAGES['en'].get(key, key))

def detect_language():
    for value in candidate_language_values():
        lang = normalize_language(value)
        if lang:
            return lang
    return 'en'

def candidate_language_values():
    value = os.environ.get('KICAD_BACKPORT_LANGUAGE')
    if value:
        yield value
    for value in kicad_config_languages():
        yield value
    for key in ('KICAD_UI_LANGUAGE', 'KICAD_LANGUAGE', 'LANGUAGE', 'LC_ALL', 'LC_MESSAGES', 'LANG'):
        value = os.environ.get(key)
        if value:
            yield value
    for value in system_locale_values():
        yield value

def system_locale_values():
    for getter in (
        lambda: locale.getlocale()[0],
        lambda: locale.getdefaultlocale()[0],
        lambda: locale.getlocale(locale.LC_CTYPE)[0],
    ):
        try:
            value = getter()
        except Exception:
            value = None
        if value:
            yield value
    if platform.system().lower() == 'windows':
        try:
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
            lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            value = locale.windows_locale.get(lang_id)
        except Exception:
            value = None
        if value:
            yield value
    elif platform.system().lower() == 'darwin':
        for value in macos_locale_values():
            yield value

def macos_locale_values():
    commands = (
        ('defaults', 'read', '-g', 'AppleLocale'),
        ('defaults', 'read', '-g', 'AppleLanguages'),
    )
    for command in commands:
        try:
            output = subprocess.check_output(command, stderr=subprocess.DEVNULL, timeout=2)
            text = output.decode('utf-8', 'replace')
        except Exception:
            continue
        for value in re.findall(r'"([^"]+)"', text):
            if value:
                yield value
        for line in text.splitlines():
            value = line.strip().strip('(),;"')
            if value and not value.startswith('('):
                yield value

def normalize_language(value):
    if not value:
        return None
    raw = str(value).strip()
    if not raw or raw.lower() == 'default':
        return None
    lowered = raw.lower().replace('-', '_')
    if raw in KICAD_LANGUAGE_LABELS:
        return KICAD_LANGUAGE_LABELS[raw]
    if lowered in KICAD_LANGUAGE_LABELS:
        return KICAD_LANGUAGE_LABELS[lowered]
    if lowered.startswith('zh_hans') or lowered.startswith('zh_cn') or lowered.startswith('zh_sg') or 'simplified' in lowered:
        return 'zh_CN'
    if lowered.startswith('zh_hant') or lowered.startswith('zh_tw') or lowered.startswith('zh_hk') or lowered.startswith('zh_mo') or ('traditional' in lowered):
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

def kicad_config_languages():
    for path in kicad_common_candidates():
        try:
            with path.open('r', encoding='utf-8') as handle:
                text = handle.read()
            payload = json.loads(text)
            language = find_language_value(payload)
            if language:
                yield str(language)
                continue
            for language in legacy_config_languages(text):
                yield language
        except Exception:
            try:
                text = path.read_text(encoding='utf-8')
            except Exception:
                continue
            for language in legacy_config_languages(text):
                yield language

def find_language_value(value):
    if isinstance(value, dict):
        system = value.get('system')
        if isinstance(system, dict):
            language = system.get('language')
            if language:
                return str(language)
        for key, child in value.items():
            if str(key).lower() == 'language' and child:
                return str(child)
            found = find_language_value(child)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = find_language_value(child)
            if found:
                return found
    return None

def legacy_config_languages(text):
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(('#', ';')):
            continue
        match = re.match('(?i)^(?:system[./\\\\])?(?:language|languageid|language_id|languagecode|language_code|locale)\\s*[:=]\\s*(.+)$', line)
        if match:
            yield match.group(1).strip().strip('"\'')

def kicad_common_candidates():
    bases = []
    for key in ('KICAD_CONFIG_HOME', 'KICAD_CONFIG_PATH'):
        value = os.environ.get(key)
        if value:
            bases.append(Path(value))
    home = Path.home()
    system = platform.system().lower()
    bases.extend(kicad_platform_config_bases(home, system, os.environ.get('APPDATA'), os.environ.get('XDG_CONFIG_HOME')))
    seen = set()
    versions = list(kicad_runtime_versions())
    for base in kicad_runtime_config_paths():
        for path in common_files_for_base(base, versions):
            key = str(path).lower()
            if key in seen:
                continue
            seen.add(key)
            yield path
    for base in bases:
        for path in common_files_for_base(base, versions):
            key = str(path).lower()
            if key in seen:
                continue
            seen.add(key)
            yield path

def kicad_platform_config_bases(home, system, appdata=None, xdg_config_home=None):
    system = (system or '').lower()
    home = Path(home)
    if system == 'windows':
        if appdata:
            yield Path(appdata) / 'kicad'
            yield Path(appdata) / 'KiCad'
    elif system == 'darwin':
        yield home / 'Library' / 'Preferences' / 'kicad'
        yield home / 'Library' / 'Preferences' / 'KiCad'
        yield home / 'Library' / 'Application Support' / 'kicad'
        yield home / 'Library' / 'Application Support' / 'KiCad'
    else:
        config_home = Path(xdg_config_home) if xdg_config_home else home / '.config'
        yield config_home / 'kicad'
        yield config_home / 'KiCad'

def kicad_runtime_config_paths():
    seen = set()

    def emit(value):
        if not value:
            return
        path = Path(str(value))
        candidates = [path]
        if path.name in ('kicad_common', 'kicad_common.json'):
            candidates.append(path.parent)
        for candidate in candidates:
            key = str(candidate).lower()
            if key in seen:
                continue
            seen.add(key)
            yield candidate
    for key in ('KICAD_BACKPORT_KICAD_CONFIG_PATH', 'KICAD_CONFIG_HOME', 'KICAD_CONFIG_PATH'):
        yield from emit(os.environ.get(key))
    try:
        import pcbnew
        getter = getattr(pcbnew, 'GetKicadConfigPath', None)
        if callable(getter):
            try:
                yield from emit(getter())
            except Exception:
                pass
    except Exception:
        pass

def kicad_runtime_versions():
    seen = set()

    def emit(value):
        if not value:
            return
        match = re.search('(\\d+)\\.(\\d+)', str(value))
        if not match:
            return
        major_minor = f'{match.group(1)}.{match.group(2)}'
        if major_minor not in seen:
            seen.add(major_minor)
            yield major_minor
        major = match.group(1)
        if major not in seen:
            seen.add(major)
            yield major
    try:
        import pcbnew
        for attr in ('GetMajorMinorVersion', 'GetBuildVersion', 'GetKicadConfigPath'):
            getter = getattr(pcbnew, attr, None)
            if callable(getter):
                try:
                    yield from emit(getter())
                except Exception:
                    pass
    except Exception:
        pass
    for key in ('KICAD_BACKPORT_KICAD_VERSION', 'KICAD_BACKPORT_KICAD_BUILD_VERSION', 'KICAD_BACKPORT_KICAD_CONFIG_PATH'):
        yield from emit(os.environ.get(key))
    for key, value in os.environ.items():
        upper = key.upper()
        if 'KICAD' in upper and ('VERSION' in upper or 'CONFIG' in upper or 'PATH' in upper):
            yield from emit(value)
    for value in (sys.executable, __file__):
        yield from emit(value)

def common_files_under(base):
    if base.exists() and base.is_file():
        yield base
        return
    names = ('kicad_common.json', 'kicad_common', 'kicad.json', 'kicad', 'pcbnew.json', 'pcbnew', 'eeschema.json', 'eeschema')
    for name in names:
        direct = base / name
        if direct.exists():
            yield direct
    if not base.exists() or not base.is_dir():
        return
    try:
        for child in base.iterdir():
            if not child.is_dir():
                continue
            for name in names:
                candidate = child / name
                if candidate.exists():
                    yield candidate
    except Exception:
        return

def common_files_for_base(base, versions):
    base = Path(base)
    if base.exists() and base.is_file():
        yield base
        return
    for version in versions:
        for path in common_files_under(base / version):
            yield path
    for path in common_files_under(base):
        yield path
