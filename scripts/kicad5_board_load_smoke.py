import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'plugin'))

from backport_core import convert  # noqa: E402


KICAD5_PYTHON = Path(r'D:\KiCad\5.0\KiCad\bin\python.exe')


def main():
    if not KICAD5_PYTHON.exists():
        print('KiCad 5 Python was not found: {0}'.format(KICAD5_PYTHON))
        return 2
    work = Path(tempfile.mkdtemp(prefix='kicad5_board_load_smoke_'))
    try:
        board = work / 'board.kicad_pcb'
        board.write_text(
            '(kicad_pcb (version 20260603) (generator "x") '
            '(generator_version "x") (paper "A4") '
            '(layers (0 "F.Cu" signal) (31 "B.Cu" signal) '
            '(32 "User.Drawings" user "Plot") (33 "User.5" user)) '
            '(setup (stackup (layer "F.Cu" (type "copper")))) '
            '(net 0 "") (net 1 "N1") '
            '(footprint "X:Y" (layer "F.Cu") '
            '(uuid "12345678-1234-1234-1234-123456789abc") '
            '(attr smd dnp) '
            '(fp_text reference "R1" (at 0 0) (layer "F.SilkS") '
            '(effects (font (size 1 1) (bold yes)))) '
            '(fp_rect (start -1 -1) (end 1 1) (stroke (width 0.12) (type default)) (layer "F.SilkS")) '
            '(fp_arc (start 0 0) (mid 1 1) (end 2 0) (stroke (width 0.1) (type default)) (layer "F.SilkS")) '
            '(pad "1" smd rect (at 0 0) (size 1 1) (layers "F.Cu" "F.Paste" "F.Mask") (net 1 "N1"))) '
            '(gr_line (start 0 0) (end 2 0) (stroke (width 0.1) (type default)) (layer "User.Drawings")) '
            '(gr_rect (start 1 1) (end 3 2) (stroke (width 0.15) (type default)) (layer "User.Drawings")) '
            '(gr_arc (start 0 2) (mid 1 3) (end 2 2) (stroke (width 0.1) (type default)) (layer "User.Drawings")) '
            '(dimension (type leader) (pts (xy 6 6) (xy 9 9)) (layer "User.Drawings") '
            '(gr_text "DIM-LOAD" (at 7 7 0) (layer "User.Drawings")) '
            '(style (thickness 0.12) (arrow_length 1))) '
            '(arc (start 10 0) (mid 15 5) (end 20 0) (width 0.2) (layer "F.Cu") (net "N1")) '
            '(zone (net "N1") (layers "F.Cu" "B.Cu") (tstamp "zone1") '
            '(hatch edge 0.508) (connect_pads (clearance 0.508)) (min_thickness 0.254) '
            '(fill yes) (polygon (pts (xy 0 0) (xy 2 0) (xy 2 2) (xy 0 2))) '
            '(filled_polygon (layer "F.Cu") (pts (xy 0 0) (xy 2 0) (xy 2 2) (xy 0 2))) '
            '(filled_polygon (layer "B.Cu") (pts (xy 0 0) (xy 2 0) (xy 2 2) (xy 0 2)))) '
            '(segment (start 0 0) (end 1 1) (width 0.2) (layer "F.Cu") (net "N1")))\n',
            encoding='utf-8',
        )
        _stdout, _stderr, code = convert(board, work / 'board_out.kicad_pcb', '5.0')
        if code != 0:
            raise RuntimeError('conversion failed')
        out = work / 'board_out_V5.kicad_pcb'
        if not out.exists():
            raise RuntimeError('converted board was not written')
        out_text = out.read_text(encoding='utf-8')
        if '(dimension' in out_text or 'DIM-LOAD' not in out_text or '(gr_line' not in out_text:
            raise RuntimeError('converted dimension graphics were not written')
        probe = (
            'import pcbnew\n'
            'board = pcbnew.LoadBoard(r"{0}")\n'
            'print(board.GetFileName())\n'
            'tracks = board.GetTracks()\n'
            'print(tracks.size() if hasattr(tracks, "size") else len(list(tracks)))\n'
        ).format(str(out))
        completed = subprocess.call([str(KICAD5_PYTHON), '-c', probe])
        if completed != 0:
            return completed
        print('kicad5 board load smoke ok')
        return 0
    finally:
        shutil.rmtree(str(work), ignore_errors=True)


if __name__ == '__main__':
    raise SystemExit(main())
