import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'plugin'))

from backport_core import convert  # noqa: E402


FIXTURE_ROOT = Path(r'E:\WORKS\MY\kicadProject\kicad-bridge\files\kicad')
KICAD5_COMPLEX_HIERARCHY = Path(r'D:\KiCad\5.0\KiCad\share\kicad\demos\complex_hierarchy')
KICAD5_PYTHON = Path(r'D:\KiCad\5.0\KiCad\bin\python.exe')
KICAD7_PYTHON = Path(r'D:\KiCad\7.0\bin\python.exe')
KICAD7_CLI = Path(r'D:\KiCad\7.0\bin\kicad-cli.exe')
KICAD10_PYTHON = Path(r'D:\KiCad\10.0\bin\python.exe')
KICAD10_CLI = Path(r'D:\KiCad\10.0\bin\kicad-cli.exe')


def _load_board(python_exe, board):
    probe = (
        'import pcbnew\n'
        'board = pcbnew.LoadBoard(r"{0}")\n'
        'print(board.GetFileName())\n'
        'tracks = board.GetTracks()\n'
        'print(tracks.size() if hasattr(tracks, "size") else len(list(tracks)))\n'
    ).format(str(board))
    return subprocess.call([str(python_exe), '-c', probe])


def _export_schematic_svg(kicad_cli, schematic, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    return subprocess.call([str(kicad_cli), 'sch', 'export', 'svg', '-o', str(output_dir), str(schematic)])


def _convert(input_path, output_path, target):
    stdout, stderr, code = convert(input_path, output_path, target)
    if code != 0:
        raise RuntimeError('conversion failed: {0}{1}'.format(stdout, stderr))


def _run_case(name, required_paths, action):
    missing = [str(path) for path in required_paths if not Path(path).exists()]
    if missing:
        print('skip {0}: missing {1}'.format(name, ', '.join(missing)))
        return False
    print('run {0}'.format(name))
    action()
    print('ok {0}'.format(name))
    return True


def main():
    work = Path(tempfile.mkdtemp(prefix='kicad_real_fixture_smoke_'))
    ran = 0
    try:
        bob = FIXTURE_ROOT / 'V5' / 'Bob_Graphics_5_0_2'
        bob_pcb = work / 'bob_out_V7' / 'Bob_Graphics_1.kicad_pcb'
        bob_sch = work / 'bob_out_V7' / 'Bob_Graphics_1.kicad_sch'

        def bob_to_v7():
            _convert(bob, work / 'bob_out', '7.0')
            if not bob_pcb.exists():
                raise RuntimeError('converted Bob_Graphics PCB was not written')
            if _load_board(KICAD7_PYTHON, bob_pcb) != 0:
                raise RuntimeError('KiCad 7 failed to load converted Bob_Graphics PCB')
            if not bob_sch.exists():
                raise RuntimeError('converted Bob_Graphics schematic was not written')
            svg_dir = work / 'bob_out_V7_svg'
            if _export_schematic_svg(KICAD7_CLI, bob_sch, svg_dir) != 0:
                raise RuntimeError('KiCad 7 failed to export converted Bob_Graphics schematic SVG')
            if not list(svg_dir.glob('*.svg')):
                raise RuntimeError('converted Bob_Graphics schematic SVG was not written')

        if _run_case('v5 Bob_Graphics project -> v7 pcb/schematic load', [bob, KICAD7_PYTHON, KICAD7_CLI], bob_to_v7):
            ran += 1

        bob10_pcb = work / 'bob_out_V10' / 'Bob_Graphics_1.kicad_pcb'
        bob10_sch = work / 'bob_out_V10' / 'Bob_Graphics_1.kicad_sch'

        def bob_to_v10():
            _convert(bob, work / 'bob_out', '10.0')
            if not bob10_pcb.exists():
                raise RuntimeError('converted Bob_Graphics V10 PCB was not written')
            if _load_board(KICAD10_PYTHON, bob10_pcb) != 0:
                raise RuntimeError('KiCad 10 failed to load upgraded Bob_Graphics PCB')
            if not bob10_sch.exists():
                raise RuntimeError('converted Bob_Graphics V10 schematic was not written')
            svg_dir = work / 'bob_out_V10_svg'
            if _export_schematic_svg(KICAD10_CLI, bob10_sch, svg_dir) != 0:
                raise RuntimeError('KiCad 10 failed to export upgraded Bob_Graphics schematic SVG')
            if not list(svg_dir.glob('*.svg')):
                raise RuntimeError('upgraded Bob_Graphics schematic SVG was not written')

        if _run_case('v5 Bob_Graphics project -> v10 pcb/schematic load', [bob, KICAD10_PYTHON, KICAD10_CLI], bob_to_v10):
            ran += 1

        complex_v7_pcb = work / 'complex_out_V7' / 'complex_hierarchy.kicad_pcb'
        complex_v7_sch = work / 'complex_out_V7' / 'complex_hierarchy.kicad_sch'

        def complex_to_v7():
            _convert(KICAD5_COMPLEX_HIERARCHY, work / 'complex_out', '7.0')
            if not complex_v7_pcb.exists():
                raise RuntimeError('converted complex_hierarchy V7 PCB was not written')
            if _load_board(KICAD7_PYTHON, complex_v7_pcb) != 0:
                raise RuntimeError('KiCad 7 failed to load upgraded complex_hierarchy PCB')
            if not complex_v7_sch.exists():
                raise RuntimeError('converted complex_hierarchy V7 schematic was not written')
            svg_dir = work / 'complex_out_V7_svg'
            if _export_schematic_svg(KICAD7_CLI, complex_v7_sch, svg_dir) != 0:
                raise RuntimeError('KiCad 7 failed to export upgraded complex_hierarchy schematic SVG')
            if not list(svg_dir.glob('*.svg')):
                raise RuntimeError('upgraded complex_hierarchy schematic SVG was not written')

        if _run_case('kicad5 complex_hierarchy project -> v7 pcb/schematic load', [KICAD5_COMPLEX_HIERARCHY, KICAD7_PYTHON, KICAD7_CLI], complex_to_v7):
            ran += 1

        complex_v10_pcb = work / 'complex_out_V10' / 'complex_hierarchy.kicad_pcb'
        complex_v10_sch = work / 'complex_out_V10' / 'complex_hierarchy.kicad_sch'

        def complex_to_v10():
            _convert(KICAD5_COMPLEX_HIERARCHY, work / 'complex_out', '10.0')
            if not complex_v10_pcb.exists():
                raise RuntimeError('converted complex_hierarchy V10 PCB was not written')
            if _load_board(KICAD10_PYTHON, complex_v10_pcb) != 0:
                raise RuntimeError('KiCad 10 failed to load upgraded complex_hierarchy PCB')
            if not complex_v10_sch.exists():
                raise RuntimeError('converted complex_hierarchy V10 schematic was not written')
            svg_dir = work / 'complex_out_V10_svg'
            if _export_schematic_svg(KICAD10_CLI, complex_v10_sch, svg_dir) != 0:
                raise RuntimeError('KiCad 10 failed to export upgraded complex_hierarchy schematic SVG')
            if not list(svg_dir.glob('*.svg')):
                raise RuntimeError('upgraded complex_hierarchy schematic SVG was not written')

        if _run_case('kicad5 complex_hierarchy project -> v10 pcb/schematic load', [KICAD5_COMPLEX_HIERARCHY, KICAD10_PYTHON, KICAD10_CLI], complex_to_v10):
            ran += 1

        bob6 = FIXTURE_ROOT / 'V6' / 'Bob_Graphics_6_0_8'
        bob6_pcb = work / 'bob6_out_V5' / 'Bob_Graphics_1.kicad_pcb'

        def bob6_to_v5():
            _convert(bob6, work / 'bob6_out', '5.0')
            if not bob6_pcb.exists():
                raise RuntimeError('converted V6 Bob_Graphics PCB was not written')
            if _load_board(KICAD5_PYTHON, bob6_pcb) != 0:
                raise RuntimeError('KiCad 5 failed to load converted V6 Bob_Graphics PCB')

        if _run_case('v6 Bob_Graphics project -> v5 pcb load', [bob6, KICAD5_PYTHON], bob6_to_v5):
            ran += 1

        bob6_v10_pcb = work / 'bob6_up_out_V10' / 'Bob_Graphics_1.kicad_pcb'
        bob6_v10_sch = work / 'bob6_up_out_V10' / 'Bob_Graphics_1.kicad_sch'

        def bob6_to_v10():
            _convert(bob6, work / 'bob6_up_out', '10.0')
            if not bob6_v10_pcb.exists():
                raise RuntimeError('converted V6 Bob_Graphics V10 PCB was not written')
            if _load_board(KICAD10_PYTHON, bob6_v10_pcb) != 0:
                raise RuntimeError('KiCad 10 failed to load upgraded V6 Bob_Graphics PCB')
            if not bob6_v10_sch.exists():
                raise RuntimeError('converted V6 Bob_Graphics V10 schematic was not written')
            svg_dir = work / 'bob6_up_out_V10_svg'
            if _export_schematic_svg(KICAD10_CLI, bob6_v10_sch, svg_dir) != 0:
                raise RuntimeError('KiCad 10 failed to export upgraded V6 Bob_Graphics schematic SVG')
            if not list(svg_dir.glob('*.svg')):
                raise RuntimeError('upgraded V6 Bob_Graphics schematic SVG was not written')

        if _run_case('v6 Bob_Graphics project -> v10 pcb/schematic load', [bob6, KICAD10_PYTHON, KICAD10_CLI], bob6_to_v10):
            ran += 1

        dat2usb = FIXTURE_ROOT / 'V7' / 'PCB_DAT2USBEXP_V7' / 'DAT2USBEXP.kicad_pcb'
        dat2usb_out = work / 'DAT2USBEXP_out_V5.kicad_pcb'

        def dat2usb_to_v5():
            _convert(dat2usb, work / 'DAT2USBEXP_out.kicad_pcb', '5.0')
            if not dat2usb_out.exists():
                raise RuntimeError('converted DAT2USBEXP PCB was not written')
            if _load_board(KICAD5_PYTHON, dat2usb_out) != 0:
                raise RuntimeError('KiCad 5 failed to load converted DAT2USBEXP PCB')

        if _run_case('v7 DAT2USBEXP board -> v5 pcb load', [dat2usb, KICAD5_PYTHON], dat2usb_to_v5):
            ran += 1

        if ran == 0:
            print('real fixture smoke skipped: no runnable local fixtures')
            return 2
        print('real fixture smoke ok ({0} case(s))'.format(ran))
        return 0
    finally:
        shutil.rmtree(str(work), ignore_errors=True)


if __name__ == '__main__':
    raise SystemExit(main())
