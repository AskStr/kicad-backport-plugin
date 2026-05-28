from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys
import threading
from pathlib import Path
from typing import List, Optional

from i18n import detect_language, translate


TARGETS = ["10.0", "9.0", "8.0", "7.0"]
MODES = ["project", "pcb", "sch"]
KICAD_FILE_EXTENSIONS = {
    ".kicad_pro",
    ".kicad_sch",
    ".kicad_pcb",
    ".kicad_sym",
    ".kicad_mod",
    ".kicad_wks",
    ".kicad_dru",
}
_WX_WINDOWS = []
WINDOW_MIN_SIZE = (760, 320)


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def plugin_icon_path(size: int = 32) -> Path:
    return project_root() / "assets" / "icons" / f"backport-light-{size}.png"


def runtime_platform() -> tuple[str, str]:
    system = platform.system().lower()
    os_map = {
        "windows": "windows",
        "cygwin": "windows",
        "msys": "windows",
        "linux": "linux",
        "darwin": "darwin",
    }
    goos = os_map.get(system, system)

    machine = (platform.machine() or "").lower()
    arch_aliases = {
        "x86_64": "amd64",
        "x64": "amd64",
        "amd64": "amd64",
        "intel64": "amd64",
        "i386": "386",
        "i686": "386",
        "x86": "386",
        "aarch64": "arm64",
        "arm64": "arm64",
        "armv8": "arm64",
    }
    goarch = arch_aliases.get(machine, machine)

    if goos == "windows":
        env_arch = (
            os.environ.get("PROCESSOR_ARCHITEW6432")
            or os.environ.get("PROCESSOR_ARCHITECTURE")
            or ""
        ).lower()
        goarch = arch_aliases.get(env_arch, goarch)

    return goos, goarch


def command_prefix(root: Path) -> list[str]:
    override = os.environ.get("KICAD_BACKPORT_BINARY", "").strip()
    if override:
        return [override]

    goos, goarch = runtime_platform()
    suffix = ".exe" if goos == "windows" else ""

    exe_names = [
        f"kicad-backport-{goos}-{goarch}{suffix}",
        f"kicad-backport-{goos}{suffix}",
        f"kicad-backport{suffix}",
        "kicad-backport.exe",
        "kicad-backport",
    ]
    for name in exe_names:
        candidate = root / "bin" / name
        if candidate.exists():
            ensure_executable(candidate, goos)
            return [str(candidate)]

    return ["go", "run", "./cmd/kicad-backport"]


def ensure_executable(path: Path, goos: str) -> None:
    if goos == "windows":
        return
    try:
        mode = path.stat().st_mode
        if mode & 0o111:
            return
        path.chmod(mode | 0o755)
    except Exception:
        pass


def hidden_subprocess_kwargs() -> dict:
    kwargs = {"stdin": subprocess.DEVNULL}
    if platform.system().lower() != "windows":
        kwargs["start_new_session"] = True
        return kwargs
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 0
    kwargs.update({
        "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0),
        "startupinfo": startupinfo,
    })
    return kwargs


def report_path_for(output_path: str) -> Path:
    report = Path(output_path)
    if report.suffix:
        return report.with_suffix(report.suffix + ".report.json")
    return report / "kicad-backport-report.json"


def target_suffix(target: str) -> str:
    value = target.strip().lower()
    if value.startswith("kicad-"):
        value = value[6:]
    if value.startswith("v"):
        value = value[1:]
    major = value
    for sep in (".", "-", "_"):
        if sep in major:
            major = major.split(sep, 1)[0]
    return "V" + major.upper() if major else ""


def versioned_output_path(output_path: str, target: str) -> str:
    label = target_suffix(target)
    if not label:
        return output_path
    path = Path(output_path)
    stem = path.stem
    if stem.upper().endswith("_" + label):
        return str(path)
    return str(path.with_name(stem + "_" + label + path.suffix))


def default_output_path(input_path: str, target: str) -> str:
    if not input_path:
        return ""
    label = target_suffix(target)
    if not label:
        return ""

    path = Path(input_path)
    parent = path.parent if path.parent != Path("") else Path.cwd()
    return str(parent / label / path.name)


def dialog_initial_dir(path_value: str) -> str:
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


def detect_current_input_path() -> str:
    return detect_default_input_path("pcb")


def detect_default_input_path(mode: str) -> str:
    if mode == "project":
        for path in kicad_project_dir_candidates():
            if path:
                return path
    if mode == "sch":
        for path in kicad_schematic_file_candidates():
            if path:
                return path
    for path in kicad_board_file_candidates():
        if path:
            return path
    return ""


def kicad_board_file_candidates():
    try:
        import pcbnew

        board = pcbnew.GetBoard()
        filename = ""
        if board is not None:
            filename = board.GetFileName() or ""
        if filename and Path(filename).suffix.lower() in KICAD_FILE_EXTENSIONS:
            yield filename
    except Exception:
        pass


def kicad_project_dir_candidates():
    for board in kicad_board_file_candidates():
        parent = Path(board).parent
        if parent.exists():
            yield str(parent)

    kiprjmod = os.environ.get("KIPRJMOD", "").strip()
    if kiprjmod and Path(kiprjmod).exists():
        yield kiprjmod


def kicad_schematic_file_candidates():
    for board in kicad_board_file_candidates():
        path = Path(board)
        same_stem = path.with_suffix(".kicad_sch")
        if same_stem.exists():
            yield str(same_stem)
        parent = path.parent
        if parent.exists():
            for candidate in sorted(parent.glob("*.kicad_sch")):
                yield str(candidate)


def mode_choices(lang: str) -> list[str]:
    return [translate(f"mode_{mode}", lang) for mode in MODES]


def mode_from_label(label: str, lang: str) -> str:
    choices = mode_choices(lang)
    try:
        return MODES[choices.index(label)]
    except ValueError:
        return "project"


def run_converter(
    input_path: str,
    output_path: str,
    target: str,
    report: Optional[str] = None,
) -> subprocess.CompletedProcess[str]:
    root = project_root()
    cmd = command_prefix(root) + [
        "convert",
        "--target-version",
        target,
        "--report",
        report or str(report_path_for(output_path)),
        input_path,
        output_path,
    ]
    return subprocess.run(
        cmd,
        cwd=str(root),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        **hidden_subprocess_kwargs(),
    )


def warning_count(stderr: str) -> int:
    return sum(1 for line in (stderr or "").splitlines() if line.strip())


def result_text(key: str, lang: str) -> str:
    value = translate(key, lang)
    if value != key:
        return value
    zh = lang.startswith("zh")
    fallbacks = {
        "complete_message": "转换已成功完成。" if zh else "Conversion completed successfully.",
        "complete_detail": "输出位置：\n{output}" if zh else "Output:\n{output}",
        "warnings_summary": (
            "有 {count} 条兼容性提示，不影响输出文件生成。详细信息已保存到：\n{report}"
            if zh
            else "{count} compatibility notice(s). The output was created. Details were saved to:\n{report}"
        ),
    }
    return fallbacks.get(key, key)


def success_message(output_path: str, report_path: str, stderr: str, lang: str) -> str:
    parts = [
        result_text("complete_message", lang),
        "",
        result_text("complete_detail", lang).format(output=output_path),
    ]
    count = warning_count(stderr)
    if count:
        parts.extend(
            [
                "",
                result_text("warnings_summary", lang).format(count=count, report=report_path),
            ]
        )
    return "\n".join(parts)


def localized_error_message(detail: str, lang: str) -> str:
    normalized = " ".join((detail or "").strip().split())
    lower = normalized.lower()
    if lower.startswith("error: "):
        lower = lower[7:]
        normalized = normalized[7:]
    if "no such file or directory" in lower or "cannot find the file" in lower or "system cannot find" in lower:
        return translate("error_input_missing", lang)
    if "permission denied" in lower or "access is denied" in lower:
        return translate("error_permission", lang)
    if "executable file not found" in lower or "file not found" in lower and "kicad-backport" in lower:
        return translate("error_cli_missing", lang)
    if "--target-version is required" in lower or "target-version is required" in lower:
        return translate("error_target_required", lang)
    if "convert requires input and output paths" in lower or "--input and --output" in lower:
        return translate("error_paths_required", lang)
    if "output directory must differ from input directory" in lower:
        return translate("error_output_dir_same", lang)
    if "output directory must not be inside input directory" in lower:
        return translate("error_output_dir_inside_input", lang)
    if "output directory must be empty or not exist" in lower:
        return translate("error_output_dir_exists", lang)
    if "output file must differ from input file" in lower:
        return translate("error_output_file_same", lang)
    if "unsupported" in lower or "not a kicad" in lower or "unknown document" in lower:
        return translate("error_invalid_kicad_file", lang)
    if not normalized:
        normalized = translate("failed_status", lang)
    template = translate("error_conversion_failed", lang)
    if template == "error_conversion_failed":
        template = "转换失败：\n{detail}" if lang.startswith("zh") else "Conversion failed:\n{detail}"
    return template.format(detail=normalized)


def converter_version() -> str:
    root = project_root()
    try:
        result = subprocess.run(
            command_prefix(root) + ["version"],
            cwd=str(root),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=3,
            **hidden_subprocess_kwargs(),
        )
    except Exception:
        return "unknown"
    value = (result.stdout or "").strip()
    return value if result.returncode == 0 and value else "unknown"


def run_cli(argv: List[str]) -> int:
    lang = detect_language()
    parser = argparse.ArgumentParser(description=translate("cli_description", lang))
    parser.add_argument("--input")
    parser.add_argument("--output")
    parser.add_argument("--target-version", default="8.0", choices=TARGETS)
    parser.add_argument("--report")
    parser.add_argument("--list-targets", action="store_true")
    ns = parser.parse_args(argv)

    if ns.list_targets:
        print("\n".join(TARGETS))
        return 0

    if not ns.input or not ns.output:
        parser.error(translate("cli_paths_required", lang))

    result = run_converter(ns.input, ns.output, ns.target_version, ns.report)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="")
    return result.returncode


def run_wx_gui(lang: str):
    tr = lambda key: translate(key, lang)

    import wx

    app = wx.GetApp()
    created_app = False
    if app is None:
        app = wx.App(False)
        created_app = True

    class BackportFrame(wx.Frame):
        def __init__(self) -> None:
            super().__init__(
                None,
                title=tr("app_title"),
                style=wx.DEFAULT_FRAME_STYLE | wx.TAB_TRAVERSAL,
            )
            panel = wx.Panel(self)
            self.SetBackgroundColour(panel.GetBackgroundColour())
            self.mode_ctrl = wx.ComboBox(
                panel,
                value=translate("mode_project", lang),
                choices=mode_choices(lang),
                style=wx.CB_READONLY,
            )
            self.input_ctrl = wx.TextCtrl(panel, size=(430, -1))
            self.output_ctrl = wx.TextCtrl(panel, size=(430, -1))
            self.target_ctrl = wx.ComboBox(panel, value="8.0", choices=TARGETS, style=wx.CB_READONLY)
            self.status_label = wx.StaticText(panel, label=tr("initial_status"))
            self.footer_label = wx.StaticText(panel, label=self.footer_text("..."))
            self.convert_button = wx.Button(panel, label=tr("convert_button"))
            file_button = wx.Button(panel, label=tr("file_button"))
            folder_button = wx.Button(panel, label=tr("folder_button"))
            save_button = wx.Button(panel, label=tr("save_as_button"))
            out_folder_button = wx.Button(panel, label=tr("folder_button"))

            for button in (file_button, folder_button, save_button, out_folder_button, self.convert_button):
                button.SetMinSize((76, -1))

            outer = wx.BoxSizer(wx.VERTICAL)

            top = wx.BoxSizer(wx.HORIZONTAL)
            top.Add(wx.StaticText(panel, label=tr("mode_label")), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
            top.Add(self.mode_ctrl, 0, wx.RIGHT, 18)
            top.Add(wx.StaticText(panel, label=tr("target_label")), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
            top.Add(self.target_ctrl, 0, wx.RIGHT, 18)
            top.AddStretchSpacer(1)
            top.Add(self.convert_button, 0, wx.ALIGN_CENTER_VERTICAL)

            input_row = wx.BoxSizer(wx.HORIZONTAL)
            input_row.Add(self.input_ctrl, 1, wx.EXPAND | wx.RIGHT, 8)
            input_row.Add(file_button, 0, wx.RIGHT, 6)
            input_row.Add(folder_button, 0)

            output_row = wx.BoxSizer(wx.HORIZONTAL)
            output_row.Add(self.output_ctrl, 1, wx.EXPAND | wx.RIGHT, 8)
            output_row.Add(save_button, 0, wx.RIGHT, 6)
            output_row.Add(out_folder_button, 0)

            outer.Add(top, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 14)
            outer.Add(wx.StaticText(panel, label=tr("input_label")), 0, wx.LEFT | wx.RIGHT | wx.TOP, 14)
            outer.Add(input_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 14)
            outer.Add(wx.StaticText(panel, label=tr("output_label")), 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
            outer.Add(output_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 14)
            outer.Add(self.status_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 14)
            outer.Add(self.footer_label, 0, wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 14)

            panel.SetSizer(outer)
            self.set_window_icon()

            file_button.Bind(wx.EVT_BUTTON, self.choose_file)
            folder_button.Bind(wx.EVT_BUTTON, self.choose_folder)
            save_button.Bind(wx.EVT_BUTTON, self.choose_output_file)
            out_folder_button.Bind(wx.EVT_BUTTON, self.choose_output_folder)
            self.mode_ctrl.Bind(wx.EVT_COMBOBOX, self.update_default_input_for_mode)
            self.convert_button.Bind(wx.EVT_BUTTON, self.convert)
            self.target_ctrl.Bind(wx.EVT_COMBOBOX, self.update_default_output)
            self.Bind(wx.EVT_CLOSE, self.on_close)

            self.fit_to_content()
            self.Centre()
            self.apply_initial_paths()
            self.load_version()

        def footer_text(self, version: str) -> str:
            return f"{tr('version_label').format(version=version)}    |    {tr('copyright')}"

        def fit_to_content(self) -> None:
            self.Layout()
            self.Fit()
            best_width, best_height = self.GetBestSize()
            width = max(WINDOW_MIN_SIZE[0], best_width)
            height = max(WINDOW_MIN_SIZE[1], best_height)
            self.SetMinSize((width, height))
            self.SetSize((width, height))
            self.Layout()

        def set_window_icon(self) -> None:
            icon = plugin_icon_path(32)
            if not icon.exists():
                return
            try:
                self.SetIcon(wx.Icon(str(icon), wx.BITMAP_TYPE_PNG))
            except Exception:
                pass

        def on_close(self, event) -> None:
            if self in _WX_WINDOWS:
                _WX_WINDOWS.remove(self)
            event.Skip()

        def apply_initial_paths(self) -> None:
            input_path = detect_default_input_path(self.selected_mode())
            if input_path:
                self.input_ctrl.SetValue(input_path)
                self.output_ctrl.SetValue(default_output_path(input_path, self.target_ctrl.GetValue()))

        def selected_mode(self) -> str:
            return mode_from_label(self.mode_ctrl.GetValue(), lang)

        def update_default_input_for_mode(self, event=None) -> None:
            input_path = detect_default_input_path(self.selected_mode())
            if input_path:
                self.input_ctrl.SetValue(input_path)
                self.update_default_output()

        def update_default_output(self, event=None) -> None:
            input_path = self.input_ctrl.GetValue().strip()
            if input_path:
                self.output_ctrl.SetValue(default_output_path(input_path, self.target_ctrl.GetValue()))

        def load_version(self) -> None:
            def worker() -> None:
                version = converter_version()
                wx.CallAfter(
                    self.update_footer,
                    self.footer_text(version),
                )

            threading.Thread(target=worker, daemon=True).start()

        def update_footer(self, text: str) -> None:
            self.footer_label.SetLabel(text)
            self.fit_to_content()

        def choose_file(self, event) -> None:
            wildcard = f"{tr('kicad_files')}|*.kicad_pro;*.kicad_sch;*.kicad_pcb;*.kicad_sym;*.kicad_mod;*.kicad_wks;*.kicad_dru|{tr('all_files')}|*.*"
            with wx.FileDialog(
                self,
                message=tr("input_label"),
                defaultDir=dialog_initial_dir(self.input_ctrl.GetValue()),
                wildcard=wildcard,
                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
            ) as dialog:
                if dialog.ShowModal() == wx.ID_OK:
                    self.input_ctrl.SetValue(dialog.GetPath())
                    self.update_default_output()

        def choose_folder(self, event) -> None:
            with wx.DirDialog(
                self,
                message=tr("input_label"),
                defaultPath=dialog_initial_dir(self.input_ctrl.GetValue()),
            ) as dialog:
                if dialog.ShowModal() == wx.ID_OK:
                    self.input_ctrl.SetValue(dialog.GetPath())
                    self.update_default_output()

        def choose_output_file(self, event) -> None:
            with wx.FileDialog(
                self,
                message=tr("output_label"),
                defaultDir=dialog_initial_dir(self.output_ctrl.GetValue()),
                style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
            ) as dialog:
                if dialog.ShowModal() == wx.ID_OK:
                    self.output_ctrl.SetValue(dialog.GetPath())

        def choose_output_folder(self, event) -> None:
            with wx.DirDialog(
                self,
                message=tr("output_label"),
                defaultPath=dialog_initial_dir(self.output_ctrl.GetValue()),
            ) as dialog:
                if dialog.ShowModal() == wx.ID_OK:
                    self.output_ctrl.SetValue(dialog.GetPath())

        def convert(self, event) -> None:
            input_path = self.input_ctrl.GetValue().strip()
            target = self.target_ctrl.GetValue().strip()
            raw_output_path = self.output_ctrl.GetValue().strip()
            if not input_path or not raw_output_path:
                wx.MessageBox(tr("missing_paths"), tr("app_title"), wx.OK | wx.ICON_ERROR, self)
                return

            output_path = versioned_output_path(raw_output_path, target)
            if Path(input_path).resolve() == Path(output_path).resolve():
                wx.MessageBox(tr("same_path_error"), tr("app_title"), wx.OK | wx.ICON_ERROR, self)
                return
            if Path(output_path).exists():
                answer = wx.MessageBox(
                    tr("overwrite_confirm"),
                    tr("app_title"),
                    wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
                    self,
                )
                if answer != wx.YES:
                    return

            self.status_label.SetLabel(tr("converting_status"))
            self.Layout()
            self.convert_button.Disable()

            def worker() -> None:
                try:
                    result = run_converter(input_path, output_path, target)
                    wx.CallAfter(self.finish_convert, result, None, output_path)
                except Exception as exc:
                    wx.CallAfter(self.finish_convert, None, exc, output_path)

            threading.Thread(target=worker, daemon=True).start()

        def finish_convert(self, result, exc, output_path: str) -> None:
            self.convert_button.Enable()
            if exc is not None:
                wx.MessageBox(localized_error_message(str(exc), lang), tr("app_title"), wx.OK | wx.ICON_ERROR, self)
                self.status_label.SetLabel(tr("failed_status"))
                self.Layout()
                return

            if result.returncode != 0:
                wx.MessageBox(
                    localized_error_message(result.stderr or result.stdout, lang),
                    tr("app_title"),
                    wx.OK | wx.ICON_ERROR,
                    self,
                )
                self.status_label.SetLabel(tr("failed_status"))
                self.Layout()
                return

            report_path = str(report_path_for(output_path))
            message = success_message(output_path, report_path, result.stderr or "", lang)
            wx.MessageBox(message, tr("app_title"), wx.OK | wx.ICON_INFORMATION, self)
            self.status_label.SetLabel(tr("complete_status"))
            self.Layout()

    frame = BackportFrame()
    _WX_WINDOWS.append(frame)
    frame.Show()
    if created_app:
        app.MainLoop()
    return 0


def run_gui() -> int:
    lang = detect_language()

    try:
        return run_wx_gui(lang)
    except Exception as exc:
        print(translate("wx_missing", lang), file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


def main() -> int:
    if len(sys.argv) > 1:
        return run_cli(sys.argv[1:])
    return run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
