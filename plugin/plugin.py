import argparse
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import List, Optional
from i18n import detect_language, translate
from backport_core import VERSION as CORE_VERSION
from backport_core import convert as convert_in_process
from backport_core import versioned_output_path as core_versioned_output_path
TARGETS = ['10.0', '9.0', '8.0', '7.0', '6.0', '5.1', '5.0', '4.0']
DEFAULT_TARGET = '7.0'
MODES = ['project', 'pcb', 'sch']
KICAD_FILE_PATTERNS = [
    '*.kicad_pro',
    '*.kicad_sch',
    '*.kicad_pcb',
    '*.kicad_sym',
    '*.kicad_mod',
    '*.kicad_wks',
    '*.kicad_dru',
    '*.sch',
    '*.lib',
    '*.dcm',
    '*.pro',
]
KICAD_FILE_EXTENSIONS = {pattern[1:].lower() for pattern in KICAD_FILE_PATTERNS}
_WX_WINDOWS = []
WINDOW_MIN_SIZE = (760, 320)

class ConversionResult:

    def __init__(self, returncode, stdout='', stderr='', output_path='', report_path=''):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.output_path = output_path
        self.report_path = report_path

def project_root():
    return Path(__file__).resolve().parents[1]

def plugin_icon_path(size=32):
    return project_root() / 'assets' / 'icons' / f'backport-light-{size}.png'

def report_path_for(output_path):
    report = Path(output_path)
    if report.suffix:
        return report.with_suffix(report.suffix + '.report.json')
    return report / 'kicad-backport-report.json'

def target_suffix(target):
    value = target.strip().lower()
    if value.startswith('kicad-'):
        value = value[6:]
    if value.startswith('v'):
        value = value[1:]
    if value == '10.99':
        return 'V10_99'
    major = value
    for sep in ('.', '-', '_'):
        if sep in major:
            major = major.split(sep, 1)[0]
    return 'V' + major.upper() if major else ''

def versioned_output_path(output_path, target):
    return str(core_versioned_output_path(output_path, target))

def default_output_path(input_path, target):
    if not input_path:
        return ''
    label = target_suffix(target)
    if not label:
        return ''
    path = Path(input_path)
    parent = path.parent if path.parent != Path('') else Path.cwd()
    return str(parent / label / path.name)

def dialog_initial_dir(path_value):
    if not path_value:
        return str(Path.home())
    path = Path(path_value)
    if path.exists():
        return str(path if path.is_dir() else path.parent)
    parent = path.parent
    while parent != parent.parent:
        if parent.exists() and parent.is_dir():
            return str(parent)
        parent = parent.parent
    return str(Path.home())

def kicad_file_patterns(separator):
    return separator.join(KICAD_FILE_PATTERNS)

def target_label(target, lang):
    key = 'target_' + target.replace('.', '_')
    label = translate(key, lang)
    if label != key:
        return label
    if target.replace('.', '', 1).isdigit():
        return 'KiCad {0}'.format(target)
    return target

def target_choices(lang):
    return [target_label(target, lang) for target in TARGETS]

def target_from_label(label, lang):
    for target in TARGETS:
        if label == target or label == target_label(target, lang):
            return target
    return label

def output_folder_for(path):
    output = Path(path)
    if output.exists() and output.is_dir():
        return output
    if output.suffix:
        return output.parent
    return output

def open_output_folder(path):
    folder = output_folder_for(path)
    if not folder.exists():
        raise FileNotFoundError(str(folder))
    if os.name == 'nt':
        os.startfile(str(folder))
    elif sys.platform == 'darwin':
        subprocess.Popen(['open', str(folder)])
    else:
        subprocess.Popen(['xdg-open', str(folder)])

def detect_current_input_path():
    return detect_default_input_path('pcb')

def detect_default_input_path(mode):
    if mode == 'project':
        for path in kicad_project_dir_candidates():
            if path:
                return path
    if mode == 'sch':
        for path in kicad_schematic_file_candidates():
            if path:
                return path
    for path in kicad_board_file_candidates():
        if path:
            return path
    return ''

def kicad_board_file_candidates():
    try:
        import pcbnew
        board = pcbnew.GetBoard()
        filename = ''
        if board is not None:
            filename = board.GetFileName() or ''
        if filename and Path(filename).suffix.lower() in KICAD_FILE_EXTENSIONS:
            yield filename
    except Exception:
        pass

def kicad_project_dir_candidates():
    for board in kicad_board_file_candidates():
        parent = Path(board).parent
        if parent.exists():
            yield str(parent)
    kiprjmod = os.environ.get('KIPRJMOD', '').strip()
    if kiprjmod and Path(kiprjmod).exists():
        yield kiprjmod

def kicad_schematic_file_candidates():
    for board in kicad_board_file_candidates():
        path = Path(board)
        same_stem = path.with_suffix('.kicad_sch')
        if same_stem.exists():
            yield str(same_stem)
        parent = path.parent
        if parent.exists():
            for candidate in sorted(parent.glob('*.kicad_sch')):
                yield str(candidate)

def mode_choices(lang):
    return [translate(f'mode_{mode}', lang) for mode in MODES]

def mode_from_label(label, lang):
    choices = mode_choices(lang)
    try:
        return MODES[choices.index(label)]
    except ValueError:
        return 'project'

def run_converter(input_path, output_path, target, report=None):
    final_output_path = versioned_output_path(output_path, target)
    report_file = report or str(report_path_for(final_output_path))
    try:
        stdout, stderr, code = convert_in_process(input_path, output_path, target, report_file)
        return ConversionResult(code, stdout, stderr, final_output_path, report_file)
    except Exception as exc:
        return ConversionResult(1, '', f'error: {exc}\n', final_output_path, report_file)

def warning_count(stderr):
    return sum((1 for line in (stderr or '').splitlines() if line.strip()))

def result_text(key, lang):
    value = translate(key, lang)
    if value != key:
        return value
    zh = lang.startswith('zh')
    fallbacks = {'complete_message': '转换已成功完成。' if zh else 'Conversion completed successfully.', 'complete_detail': '输出位置：\n{output}' if zh else 'Output:\n{output}', 'warnings_summary': '有 {count} 条兼容性提示，不影响输出文件生成。详细信息已保存到：\n{report}' if zh else '{count} compatibility notice(s). The output was created. Details were saved to:\n{report}'}
    return fallbacks.get(key, key)

def success_message(output_path, report_path, stderr, lang):
    parts = [result_text('complete_message', lang), '', result_text('complete_detail', lang).format(output=output_path)]
    count = warning_count(stderr)
    if count:
        parts.extend(['', result_text('warnings_summary', lang).format(count=count, report=report_path)])
    return '\n'.join(parts)

def localized_error_message(detail, lang):
    normalized = ' '.join((detail or '').strip().split())
    lower = normalized.lower()
    if lower.startswith('error: '):
        lower = lower[7:]
        normalized = normalized[7:]
    if 'no such file or directory' in lower or 'cannot find the file' in lower or 'system cannot find' in lower:
        return translate('error_input_missing', lang)
    if 'permission denied' in lower or 'access is denied' in lower:
        return translate('error_permission', lang)
    if 'executable file not found' in lower or ('file not found' in lower and 'kicad-backport' in lower):
        return translate('error_cli_missing', lang)
    if '--target-version is required' in lower or 'target-version is required' in lower:
        return translate('error_target_required', lang)
    if 'convert requires input and output paths' in lower or '--input and --output' in lower:
        return translate('error_paths_required', lang)
    if 'output directory must differ from input directory' in lower:
        return translate('error_output_dir_same', lang)
    if 'output directory must not be inside input directory' in lower:
        return translate('error_output_dir_inside_input', lang)
    if 'output directory must be empty or not exist' in lower:
        return translate('error_output_dir_exists', lang)
    if 'output file must differ from input file' in lower:
        return translate('error_output_file_same', lang)
    if 'unsupported' in lower or 'not a kicad' in lower or 'unknown document' in lower:
        return translate('error_invalid_kicad_file', lang)
    if not normalized:
        normalized = translate('failed_status', lang)
    template = translate('error_conversion_failed', lang)
    if template == 'error_conversion_failed':
        template = '转换失败：\n{detail}' if lang.startswith('zh') else 'Conversion failed:\n{detail}'
    return template.format(detail=normalized)

def converter_version():
    return CORE_VERSION

def run_cli(argv):
    lang = detect_language()
    parser = argparse.ArgumentParser(description=translate('cli_description', lang))
    parser.add_argument('--input')
    parser.add_argument('--output')
    parser.add_argument('--target-version', default=DEFAULT_TARGET)
    parser.add_argument('--report')
    parser.add_argument('--list-targets', action='store_true')
    ns = parser.parse_args(argv)
    if ns.list_targets:
        print('\n'.join(TARGETS))
        return 0
    if not ns.input or not ns.output:
        parser.error(translate('cli_paths_required', lang))
    result = run_converter(ns.input, ns.output, ns.target_version, ns.report)
    if result.stdout:
        print(result.stdout, end='')
    if result.stderr:
        print(result.stderr, file=sys.stderr, end='')
    return result.returncode

def run_wx_gui(lang):
    tr = lambda key: translate(key, lang)
    import wx
    app = wx.GetApp()
    created_app = False
    if app is None:
        app = wx.App(False)
        created_app = True

    class BackportFrame(wx.Frame):

        def __init__(self):
            super().__init__(None, title=tr('app_title'), style=wx.DEFAULT_FRAME_STYLE | wx.TAB_TRAVERSAL)
            panel = wx.Panel(self)
            self.SetBackgroundColour(panel.GetBackgroundColour())
            self.mode_ctrl = wx.ComboBox(panel, value=translate('mode_project', lang), choices=mode_choices(lang), style=wx.CB_READONLY)
            self.input_ctrl = wx.TextCtrl(panel, size=(430, -1))
            self.output_ctrl = wx.TextCtrl(panel, size=(430, -1))
            self.target_ctrl = wx.ComboBox(panel, value=target_label(DEFAULT_TARGET, lang), choices=target_choices(lang), style=wx.CB_READONLY)
            self.status_label = wx.StaticText(panel, label=tr('initial_status'))
            self.footer_label = wx.StaticText(panel, label=self.footer_text('...'))
            self.convert_button = wx.Button(panel, label=tr('convert_button'))
            self.open_output_button = wx.Button(panel, label=tr('open_output_button'))
            self.open_output_button.Disable()
            self.last_output_path = ''
            file_button = wx.Button(panel, label=tr('file_button'))
            folder_button = wx.Button(panel, label=tr('folder_button'))
            save_button = wx.Button(panel, label=tr('save_as_button'))
            out_folder_button = wx.Button(panel, label=tr('folder_button'))

            def set_button_width(button):
                text_width, _text_height = button.GetTextExtent(button.GetLabel())
                button.SetMinSize((max(88, text_width + 34), -1))

            for button in (file_button, folder_button, save_button, out_folder_button, self.convert_button, self.open_output_button):
                set_button_width(button)
            self.mode_ctrl.SetMinSize((max(150, self.mode_ctrl.GetBestSize().GetWidth()), -1))
            self.target_ctrl.SetMinSize((max(126, self.target_ctrl.GetBestSize().GetWidth()), -1))
            outer = wx.BoxSizer(wx.VERTICAL)
            top = wx.BoxSizer(wx.HORIZONTAL)
            top.Add(wx.StaticText(panel, label=tr('mode_label')), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
            top.Add(self.mode_ctrl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 24)
            top.Add(wx.StaticText(panel, label=tr('target_label')), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
            top.Add(self.target_ctrl, 0, wx.ALIGN_CENTER_VERTICAL)
            action_row = wx.BoxSizer(wx.HORIZONTAL)
            action_row.AddStretchSpacer(1)
            action_row.Add(self.open_output_button, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
            action_row.Add(self.convert_button, 0, wx.ALIGN_CENTER_VERTICAL)
            input_row = wx.BoxSizer(wx.HORIZONTAL)
            input_row.Add(self.input_ctrl, 1, wx.EXPAND | wx.RIGHT, 8)
            input_row.Add(file_button, 0, wx.RIGHT, 6)
            input_row.Add(folder_button, 0)
            output_row = wx.BoxSizer(wx.HORIZONTAL)
            output_row.Add(self.output_ctrl, 1, wx.EXPAND | wx.RIGHT, 8)
            output_row.Add(save_button, 0, wx.RIGHT, 6)
            output_row.Add(out_folder_button, 0)
            outer.Add(top, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 14)
            outer.Add(action_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)
            outer.Add(wx.StaticText(panel, label=tr('input_label')), 0, wx.LEFT | wx.RIGHT | wx.TOP, 14)
            outer.Add(input_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 14)
            outer.Add(wx.StaticText(panel, label=tr('output_label')), 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
            outer.Add(output_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 14)
            outer.Add(self.status_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 14)
            outer.Add(self.footer_label, 0, wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 14)
            panel.SetSizer(outer)
            self.set_window_icon()
            file_button.Bind(wx.EVT_BUTTON, self.choose_file)
            folder_button.Bind(wx.EVT_BUTTON, self.choose_folder)
            save_button.Bind(wx.EVT_BUTTON, self.choose_output_file)
            out_folder_button.Bind(wx.EVT_BUTTON, self.choose_output_folder)
            self.open_output_button.Bind(wx.EVT_BUTTON, self.open_output)
            self.mode_ctrl.Bind(wx.EVT_COMBOBOX, self.update_default_input_for_mode)
            self.convert_button.Bind(wx.EVT_BUTTON, self.convert)
            self.target_ctrl.Bind(wx.EVT_COMBOBOX, self.update_default_output)
            self.Bind(wx.EVT_CLOSE, self.on_close)
            self.fit_to_content()
            self.Centre()
            self.apply_initial_paths()
            self.load_version()

        def footer_text(self, version):
            return f"{tr('version_label').format(version=version)}    |    {tr('copyright')}"

        def fit_to_content(self):
            self.Layout()
            self.Fit()
            best_width, best_height = self.GetBestSize()
            width = max(WINDOW_MIN_SIZE[0], best_width)
            height = max(WINDOW_MIN_SIZE[1], best_height)
            self.SetMinSize((width, height))
            self.SetSize((width, height))
            self.Layout()

        def set_window_icon(self):
            icon = plugin_icon_path(32)
            if not icon.exists():
                return
            try:
                self.SetIcon(wx.Icon(str(icon), wx.BITMAP_TYPE_PNG))
            except Exception:
                pass

        def on_close(self, event):
            if self in _WX_WINDOWS:
                _WX_WINDOWS.remove(self)
            event.Skip()

        def apply_initial_paths(self):
            input_path = detect_default_input_path(self.selected_mode())
            if input_path:
                self.input_ctrl.SetValue(input_path)
                self.output_ctrl.SetValue(default_output_path(input_path, target_from_label(self.target_ctrl.GetValue(), lang)))

        def selected_mode(self):
            return mode_from_label(self.mode_ctrl.GetValue(), lang)

        def update_default_input_for_mode(self, event=None):
            input_path = detect_default_input_path(self.selected_mode())
            if input_path:
                self.input_ctrl.SetValue(input_path)
                self.update_default_output()

        def update_default_output(self, event=None):
            input_path = self.input_ctrl.GetValue().strip()
            if input_path:
                self.output_ctrl.SetValue(default_output_path(input_path, target_from_label(self.target_ctrl.GetValue(), lang)))

        def open_output(self, event):
            try:
                open_output_folder(self.last_output_path)
            except Exception as exc:
                wx.MessageBox(tr('open_output_error').format(detail=exc), tr('app_title'), wx.OK | wx.ICON_ERROR, self)

        def load_version(self):

            def worker():
                version = converter_version()
                wx.CallAfter(self.update_footer, self.footer_text(version))
            threading.Thread(target=worker, daemon=True).start()

        def update_footer(self, text):
            self.footer_label.SetLabel(text)
            self.fit_to_content()

        def choose_file(self, event):
            wildcard = f"{tr('kicad_files')}|{kicad_file_patterns(';')}|{tr('all_files')}|*.*"
            with wx.FileDialog(self, message=tr('input_label'), defaultDir=dialog_initial_dir(self.input_ctrl.GetValue()), wildcard=wildcard, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as dialog:
                if dialog.ShowModal() == wx.ID_OK:
                    self.input_ctrl.SetValue(dialog.GetPath())
                    self.update_default_output()

        def choose_folder(self, event):
            with wx.DirDialog(self, message=tr('input_label'), defaultPath=dialog_initial_dir(self.input_ctrl.GetValue())) as dialog:
                if dialog.ShowModal() == wx.ID_OK:
                    self.input_ctrl.SetValue(dialog.GetPath())
                    self.update_default_output()

        def choose_output_file(self, event):
            with wx.FileDialog(self, message=tr('output_label'), defaultDir=dialog_initial_dir(self.output_ctrl.GetValue()), style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as dialog:
                if dialog.ShowModal() == wx.ID_OK:
                    self.output_ctrl.SetValue(dialog.GetPath())

        def choose_output_folder(self, event):
            with wx.DirDialog(self, message=tr('output_label'), defaultPath=dialog_initial_dir(self.output_ctrl.GetValue())) as dialog:
                if dialog.ShowModal() == wx.ID_OK:
                    self.output_ctrl.SetValue(dialog.GetPath())

        def convert(self, event):
            input_path = self.input_ctrl.GetValue().strip()
            target = target_from_label(self.target_ctrl.GetValue().strip(), lang)
            raw_output_path = self.output_ctrl.GetValue().strip()
            if not input_path or not raw_output_path:
                wx.MessageBox(tr('missing_paths'), tr('app_title'), wx.OK | wx.ICON_ERROR, self)
                return
            output_path = versioned_output_path(raw_output_path, target)
            if Path(input_path).resolve() == Path(output_path).resolve():
                wx.MessageBox(tr('same_path_error'), tr('app_title'), wx.OK | wx.ICON_ERROR, self)
                return
            if Path(output_path).exists():
                answer = wx.MessageBox(tr('overwrite_confirm'), tr('app_title'), wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION, self)
                if answer != wx.YES:
                    return
            self.status_label.SetLabel(tr('converting_status'))
            self.Layout()
            self.convert_button.Disable()
            self.open_output_button.Disable()

            def worker():
                try:
                    result = run_converter(input_path, raw_output_path, target)
                    wx.CallAfter(self.finish_convert, result, None, output_path)
                except Exception as exc:
                    wx.CallAfter(self.finish_convert, None, exc, output_path)
            threading.Thread(target=worker, daemon=True).start()

        def finish_convert(self, result, exc, output_path):
            self.convert_button.Enable()
            if exc is not None:
                wx.MessageBox(localized_error_message(str(exc), lang), tr('app_title'), wx.OK | wx.ICON_ERROR, self)
                self.status_label.SetLabel(tr('failed_status'))
                self.Layout()
                return
            if result.returncode != 0:
                wx.MessageBox(localized_error_message(result.stderr or result.stdout, lang), tr('app_title'), wx.OK | wx.ICON_ERROR, self)
                self.status_label.SetLabel(tr('failed_status'))
                self.Layout()
                return
            final_output_path = result.output_path or output_path
            report_path = result.report_path or str(report_path_for(final_output_path))
            message = success_message(final_output_path, report_path, result.stderr or '', lang)
            wx.MessageBox(message, tr('app_title'), wx.OK | wx.ICON_INFORMATION, self)
            self.last_output_path = final_output_path
            self.open_output_button.Enable()
            self.status_label.SetLabel(tr('complete_status'))
            self.Layout()
    frame = BackportFrame()
    _WX_WINDOWS.append(frame)
    frame.Show()
    if created_app:
        app.MainLoop()
    return 0

def run_tk_gui(lang):
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    tr = lambda key: translate(key, lang)
    root = tk.Tk()
    root.title(tr('app_title'))
    icon = plugin_icon_path(32)
    if icon.exists():
        try:
            icon_image = tk.PhotoImage(file=str(icon))
            root.iconphoto(True, icon_image)
            root._kicad_backport_icon = icon_image
        except Exception:
            pass
    root.minsize(*WINDOW_MIN_SIZE)
    mode_var = tk.StringVar(value=translate('mode_project', lang))
    input_var = tk.StringVar()
    output_var = tk.StringVar()
    target_var = tk.StringVar(value=target_label(DEFAULT_TARGET, lang))
    status_var = tk.StringVar(value=tr('initial_status'))
    footer_var = tk.StringVar(value=f"{tr('version_label').format(version='...')}    |    {tr('copyright')}")
    last_output_path = {'path': ''}

    def selected_mode():
        return mode_from_label(mode_var.get(), lang)

    def update_default_output(*_args):
        input_path = input_var.get().strip()
        if input_path:
            output_var.set(default_output_path(input_path, target_from_label(target_var.get(), lang)))

    def update_default_input(*_args):
        input_path = detect_default_input_path(selected_mode())
        if input_path:
            input_var.set(input_path)
            update_default_output()

    def choose_file():
        path = filedialog.askopenfilename(title=tr('input_label'), initialdir=dialog_initial_dir(input_var.get()), filetypes=[(tr('kicad_files'), kicad_file_patterns(' ')), (tr('all_files'), '*.*')])
        if path:
            input_var.set(path)
            update_default_output()

    def choose_folder():
        path = filedialog.askdirectory(title=tr('input_label'), initialdir=dialog_initial_dir(input_var.get()))
        if path:
            input_var.set(path)
            update_default_output()

    def choose_output_file():
        path = filedialog.asksaveasfilename(title=tr('output_label'), initialdir=dialog_initial_dir(output_var.get()))
        if path:
            output_var.set(path)

    def choose_output_folder():
        path = filedialog.askdirectory(title=tr('output_label'), initialdir=dialog_initial_dir(output_var.get()))
        if path:
            output_var.set(path)

    def open_output():
        try:
            open_output_folder(last_output_path['path'])
        except Exception as exc:
            messagebox.showerror(tr('app_title'), tr('open_output_error').format(detail=exc), parent=root)
    outer = ttk.Frame(root, padding=14)
    outer.grid(row=0, column=0, sticky='nsew')
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    outer.columnconfigure(0, weight=1)
    mode_width = max(16, max((len(choice) for choice in mode_choices(lang)), default=0) + 2)
    target_width = max(12, max((len(choice) for choice in target_choices(lang)), default=0) + 2)
    small_button_width = max(8, len(tr('save_as_button')) + 2, len(tr('folder_button')) + 2, len(tr('file_button')) + 2)
    action_button_width = max(10, len(tr('convert_button')) + 2, len(tr('open_output_button')) + 2)

    top = ttk.Frame(outer)
    top.grid(row=0, column=0, sticky='ew')
    top.columnconfigure(4, weight=1)
    ttk.Label(top, text=tr('mode_label')).grid(row=0, column=0, sticky='w', padx=(0, 8))
    mode_combo = ttk.Combobox(top, textvariable=mode_var, values=mode_choices(lang), state='readonly', width=mode_width)
    mode_combo.grid(row=0, column=1, sticky='w')
    ttk.Label(top, text=tr('target_label')).grid(row=0, column=2, sticky='w', padx=(22, 8))
    target_combo = ttk.Combobox(top, textvariable=target_var, values=target_choices(lang), state='readonly', width=target_width)
    target_combo.grid(row=0, column=3, sticky='w')

    actions = ttk.Frame(outer)
    actions.grid(row=1, column=0, sticky='ew', pady=(10, 0))
    actions.columnconfigure(0, weight=1)
    open_button = ttk.Button(actions, text=tr('open_output_button'), command=open_output, state='disabled', width=action_button_width)
    open_button.grid(row=0, column=1, sticky='e', padx=(0, 8))
    convert_button = ttk.Button(actions, text=tr('convert_button'), width=action_button_width)
    convert_button.grid(row=0, column=2, sticky='e')

    ttk.Label(outer, text=tr('input_label')).grid(row=2, column=0, sticky='w', pady=(14, 0))
    input_row = ttk.Frame(outer)
    input_row.grid(row=3, column=0, sticky='ew', pady=(8, 0))
    input_row.columnconfigure(0, weight=1)
    ttk.Entry(input_row, textvariable=input_var).grid(row=0, column=0, sticky='ew', padx=(0, 8))
    ttk.Button(input_row, text=tr('file_button'), command=choose_file, width=small_button_width).grid(row=0, column=1, sticky='e', padx=(0, 6))
    ttk.Button(input_row, text=tr('folder_button'), command=choose_folder, width=small_button_width).grid(row=0, column=2, sticky='e')

    ttk.Label(outer, text=tr('output_label')).grid(row=4, column=0, sticky='w', pady=(12, 0))
    output_row = ttk.Frame(outer)
    output_row.grid(row=5, column=0, sticky='ew', pady=(8, 0))
    output_row.columnconfigure(0, weight=1)
    ttk.Entry(output_row, textvariable=output_var).grid(row=0, column=0, sticky='ew', padx=(0, 8))
    ttk.Button(output_row, text=tr('save_as_button'), command=choose_output_file, width=small_button_width).grid(row=0, column=1, sticky='e', padx=(0, 6))
    ttk.Button(output_row, text=tr('folder_button'), command=choose_output_folder, width=small_button_width).grid(row=0, column=2, sticky='e')

    ttk.Label(outer, textvariable=status_var).grid(row=6, column=0, sticky='w', pady=(14, 0))
    ttk.Label(outer, textvariable=footer_var).grid(row=7, column=0, sticky='w', pady=(14, 0))

    def finish_convert(result, exc, output_path):
        convert_button.state(['!disabled'])
        if exc is not None:
            messagebox.showerror(tr('app_title'), localized_error_message(str(exc), lang), parent=root)
            status_var.set(tr('failed_status'))
            return
        if result.returncode != 0:
            messagebox.showerror(tr('app_title'), localized_error_message(result.stderr or result.stdout, lang), parent=root)
            status_var.set(tr('failed_status'))
            return
        final_output_path = result.output_path or output_path
        report_path = result.report_path or str(report_path_for(final_output_path))
        messagebox.showinfo(tr('app_title'), success_message(final_output_path, report_path, result.stderr or '', lang), parent=root)
        last_output_path['path'] = final_output_path
        open_button.state(['!disabled'])
        status_var.set(tr('complete_status'))

    def convert():
        input_path = input_var.get().strip()
        raw_output_path = output_var.get().strip()
        target = target_from_label(target_var.get().strip(), lang)
        if not input_path or not raw_output_path:
            messagebox.showerror(tr('app_title'), tr('missing_paths'), parent=root)
            return
        output_path = versioned_output_path(raw_output_path, target)
        if Path(input_path).resolve() == Path(output_path).resolve():
            messagebox.showerror(tr('app_title'), tr('same_path_error'), parent=root)
            return
        if Path(output_path).exists() and (not messagebox.askyesno(tr('app_title'), tr('overwrite_confirm'), parent=root)):
            return
        status_var.set(tr('converting_status'))
        convert_button.state(['disabled'])
        open_button.state(['disabled'])

        def worker():
            try:
                result = run_converter(input_path, raw_output_path, target)
                root.after(0, finish_convert, result, None, output_path)
            except Exception as exc:
                root.after(0, finish_convert, None, exc, output_path)
        threading.Thread(target=worker, daemon=True).start()

    def load_version():
        version = converter_version()
        root.after(0, footer_var.set, f"{tr('version_label').format(version=version)}    |    {tr('copyright')}")
    convert_button.configure(command=convert)
    mode_combo.bind('<<ComboboxSelected>>', update_default_input)
    target_combo.bind('<<ComboboxSelected>>', update_default_output)
    update_default_input()
    threading.Thread(target=load_version, daemon=True).start()
    root.mainloop()
    return 0

def _safe_stderr(message):
    stream = getattr(sys, 'stderr', None)
    if stream is None:
        return
    try:
        print(message, file=stream)
    except Exception:
        pass

def gui_backend_order():
    raw = os.environ.get('KICAD_BACKPORT_GUI_BACKEND', '').strip().lower()
    if raw:
        result = []
        for item in raw.replace(';', ',').split(','):
            name = item.strip()
            if name in ('auto', 'default'):
                result.extend(['wx', 'tk'])
            elif name in ('legacy', 'kicad5'):
                result.extend(['tk', 'wx'])
            elif name in ('wx', 'tk') and name not in result:
                result.append(name)
        if result:
            return result
    if os.environ.get('KICAD_BACKPORT_LEGACY', '').strip():
        return ['tk', 'wx']
    return ['wx', 'tk']

def run_gui():
    lang = detect_language()
    runners = {'wx': run_wx_gui, 'tk': run_tk_gui}
    errors = []
    for backend in gui_backend_order():
        runner = runners.get(backend)
        if runner is None:
            continue
        try:
            return runner(lang)
        except Exception as exc:
            errors.append('{0}: {1}'.format(backend, exc))
            if backend == 'wx':
                _safe_stderr(translate('wx_missing', lang))
            _safe_stderr('{0}: {1}'.format(backend, exc))
    if errors:
        _safe_stderr('No GUI backend could be started: {0}'.format('; '.join(errors)))
    return 1

def main():
    if len(sys.argv) > 1:
        return run_cli(sys.argv[1:])
    return run_gui()
if __name__ == '__main__':
    raise SystemExit(main())
