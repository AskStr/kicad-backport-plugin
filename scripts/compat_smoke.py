import shutil
import sys
import tempfile
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugin"))

from backport_core import convert, resolve_target_version, versioned_output_path  # noqa: E402


def main():
    work = Path(tempfile.mkdtemp(prefix="kicad_backport_plugin_smoke_"))
    try:
        assert resolve_target_version("board", "10.99") == "20260603"
        assert resolve_target_version("board", "20260521") == "20260521"
        assert resolve_target_version("schematic", "20260521") == "20260306"
        assert resolve_target_version("symbol-library", "20260603") == "20251024"
        assert resolve_target_version("board", "5.0") == "20171130"
        assert versioned_output_path(work / "demo.kicad_sch", "5.0").name == "demo_V5.sch"
        assert versioned_output_path(work / "demo.kicad_pcb", "20260521").name == "demo_V20260521.kicad_pcb"

        pcb = work / "board.kicad_pcb"
        pcb.write_text(
            '(kicad_pcb (version 20260603) '
            '(generator_version "x") (paper "A4") '
            '(layers (0 "F.Cu" signal) (31 "B.Cu" signal) '
            '(32 "User.Drawings" user "Plot") (33 "User.5" user)) '
            '(setup (allow_soldermask_bridges_in_footprints yes) (stackup (layer "F.Cu" (type "copper")))) '
            '(net 0 "") (net 1 "N1") '
            '(footprint "X:Y" (layer "F.Cu") '
            '(uuid "12345678-1234-1234-1234-123456789abc") '
            '(attr smd dnp allow_missing_courtyard) '
            '(property "Reference" "RPROP" (at 1 1 0) (effects (font (size 1 1)) hide)) '
            '(property "Custom" "C" (at 0 0 0)) '
            '(group "g1") (zone (keepout (tracks not_allowed))) '
            '(net_tie_pad_groups "1") (units "U") '
            '(fp_text reference "R1" (at 0 0) (layer "F.SilkS") '
            '(uuid "abcdef12-3456-7890-abcd-ef1234567890") '
            '(effects (font (size 1 1) (bold yes)))) '
            '(fp_rect (start -1 -1) (end 1 1) (stroke (width 0.12) (type default)) (layer "F.SilkS")) '
            '(fp_circle (center 0 0) (end 0 1) (width 0.1) (fill none) (layer "F.SilkS")) '
            '(model "demo.wrl" (offset (xyz 25.4 50.8 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)) (opacity 0.5)) '
            '(pad "1" smd custom locked (at 0 0) (size 1 1) (layers "F.Cu" "F.Paste" "F.Mask") '
            '(net "N1") (thermal_bridge_angle 45) (sim_electrical_type passive) '
            '(thermal_bridge_width 0.6) '
            '(pinfunction "IO") (pintype "bidirectional") (property pad_prop) '
            '(uuid "11111111-2222-3333-4444-555555555555") '
            '(chamfer top_left) (chamfer_ratio 0.2) (roundrect_rratio 0.25) '
            '(options (clearance outline) (anchor rect)) '
            '(primitives (gr_line (start -0.5 0) (end 0.5 0) (width 0.1)))) '
            '(fp_arc (start 0 0) (mid 1 1) (end 2 0) (stroke (width 0.1) (type default)) (layer "F.SilkS"))) '
            '(gr_line (start 0 0) (end 2 0) (stroke (width 0.1) (type default)) (layer "User.Drawings")) '
            '(gr_rect (start 1 1) (end 3 2) (stroke (width 0.15) (type default)) (layer "User.Drawings")) '
            '(gr_rect (start 4 4) (end 6 5) (stroke (width 0.12) (type default)) (fill solid) (layer "F.Cu") (net "N1")) '
            '(gr_arc (start 0 2) (mid 1 3) (end 2 2) (stroke (width 0.1) (type default)) (layer "User.Drawings")) '
            '(gr_text "T" (at 0 0 0) (layer "F.SilkS") (render_cache (polygon (pts (xy 0 0))))) '
            '(table_cell "C" (knockout yes)) '
            '(dimension (type orthogonal) (pts (xy 0 10) (xy 10 20)) (height 2) '
            '(orientation 1) (layer "User.Drawings") '
            '(gr_text "DIM-ORTHO" (at 5 15 0) (layer "User.Drawings")) '
            '(style (thickness 0.12) (arrow_length 1) (extension_height 0.5) '
            '(arrow_direction outward) (suppress_zeroes yes) (keep_text_aligned no))) '
            '(dimension (type leader) (pts (xy 20 20) (xy 25 25)) (layer "User.Drawings") '
            '(gr_text "DIM-LEADER" (at 22 22 0) (layer "User.Drawings")) '
            '(style (thickness 0.12) (arrow_length 1))) '
            '(arc (start 10 0) (mid 15 5) (end 20 0) (width 0.2) (layer "F.Cu") (net "N1")) '
            '(zone (net "N1") (layers "F.Cu" "B.Cu") (tstamp "zone1") (name "Z") (attr) '
            '(hatch edge 0.508) (connect_pads (clearance 0.508)) (min_thickness 0.254) '
            '(fill yes (island_removal_mode 1) (island_area_min 2)) '
            '(polygon (pts (xy 0 0) (xy 2 0) (xy 2 2) (xy 0 2))) '
            '(filled_polygon (layer "F.Cu") (pts (xy 0 0) (xy 2 0) (xy 2 2) (xy 0 2))) '
            '(filled_polygon (layer "B.Cu") (pts (xy 0 0) (xy 2 0) (xy 2 2) (xy 0 2)))) '
            '(zone (keepout (tracks not_allowed))) '
            '(via (at 4 4) (size 0.8) (drill 0.4) (layers "F.Cu" "B.Cu") free (net "N1")) '
            '(segment (start 0 0) (end 1 1) (width 0.2) (layer "F.Cu") (net "")))\n',
            encoding="utf-8",
        )
        _out, _err, code = convert(pcb, work / "board_out.kicad_pcb", "5.0", work / "pcb_report.json")
        assert code == 0
        board_v5 = work / "board_out_V5.kicad_pcb"
        assert board_v5.exists()
        board_text = board_v5.read_text(encoding="utf-8")
        board_compact = " ".join(board_text.split())
        assert "(version 20171130)" in board_text
        assert "(host pcbnew 5.0.2)" in board_text
        assert "(page A4)" in board_text
        assert "(module" in board_text and '"X:Y"' in board_text
        assert "(footprint" not in board_text
        assert "(tstamp 12345678)" in board_text
        assert '(fp_text reference "RPROP" hide' in board_compact
        assert "(attr" not in board_text
        assert '"Custom"' not in board_text
        assert "net_tie_pad_groups" not in board_text
        assert "(units" not in board_text
        assert "thermal_bridge_angle" not in board_text
        assert "thermal_bridge_width" not in board_text
        assert "(thermal_width 0.6)" in board_text
        assert "sim_electrical_type" not in board_text
        assert "\n      locked\n" not in board_text
        assert "pinfunction" not in board_text
        assert "pintype" not in board_text
        assert "chamfer" not in board_text
        assert "pad_prop" not in board_text
        assert "11111111" not in board_text
        assert "abcdef12" not in board_text
        assert "(fill none)" not in board_text
        assert "(opacity" not in board_text
        assert "free" not in board_text
        assert "Dwgs.User" in board_text
        assert "User.Drawings" not in board_text
        assert "User.5" not in board_text
        assert "stackup" not in board_text
        assert "allow_soldermask_bridges_in_footprints" not in board_text
        assert "render_cache" not in board_text
        assert "knockout" not in board_text
        assert "keepout" not in board_text
        assert "(dimension" not in board_text
        assert "DIM-ORTHO" in board_text
        assert "DIM-LEADER" in board_text
        assert "arrow_direction" not in board_text
        assert "suppress_zeroes" not in board_text
        assert "keep_text_aligned" not in board_text
        assert "(stroke" not in board_text
        assert "(width 0.1)" in board_text
        assert "(gr_rect" not in board_text
        assert "(fp_rect" not in board_text
        assert "(fp_line" in board_text
        assert "(mid" not in board_text
        assert "(angle" in board_text
        assert "(arc" not in board_text
        assert board_text.count("(segment") >= 10
        assert '(net 1)' in board_text
        assert board_text.count("(zone") == 3
        assert "(layer F.Cu)" in board_text
        assert "(layer B.Cu)" in board_text
        assert "(tstamp zone1)" in board_text
        assert '(tstamp "zone1")' not in board_text
        assert board_text.count("(filled_polygon") == 3
        assert "(filled_polygon (layer" not in board_text
        assert "(xy 4 4)" in board_text and "(xy 6 5)" in board_text
        assert '(net_name "N1")' in board_text
        assert '(name "Z")' not in board_text
        assert "filled_areas_thickness" not in board_text
        assert "(attr)" not in board_text
        assert "island_removal_mode" not in board_text
        assert "island_area_min" not in board_text
        assert "generator_version" not in board_text

        _out, _err, code = convert(pcb, work / "board9_out.kicad_pcb", "9.0")
        assert code == 0
        board_v9 = work / "board9_out_V9.kicad_pcb"
        assert board_v9.exists()
        board9_text = board_v9.read_text(encoding="utf-8")
        assert "Dwgs.User" in board9_text
        assert "User.Drawings" not in board9_text
        assert "User.5" not in board9_text

        _out, _err, code = convert(pcb, work / "board4_out.kicad_pcb", "4.0")
        assert code == 0
        board_v4 = work / "board4_out_V4.kicad_pcb"
        assert board_v4.exists()
        board4_text = board_v4.read_text(encoding="utf-8")
        assert "(version 4)" in board4_text
        assert "(offset" not in board4_text
        assert "(at" in board4_text
        assert "(xyz 1 2 0)" in board4_text
        assert "custom" not in board4_text
        assert "\n      rect\n" in board4_text
        assert "(primitives" not in board4_text
        assert "(options" not in board4_text
        assert "roundrect_rratio" not in board4_text
        assert '(net_name "N1")' in board4_text

        teardrop = work / "teardrop.kicad_pcb"
        teardrop.write_text(
            '(kicad_pcb (version 20241229) (generator "x") (paper "A4") '
            '(layers (0 "F.Cu" signal)) '
            '(legacy_teardrops no) '
            '(teardrops (curved_edges yes)))\n',
            encoding="utf-8",
        )
        _out, _err, code = convert(teardrop, work / "teardrop_out.kicad_pcb", "8.0")
        assert code == 0
        teardrop_text = (work / "teardrop_out_V8.kicad_pcb").read_text(encoding="utf-8")
        assert "(version 20240108)" in teardrop_text
        assert "curved_edges" not in teardrop_text
        assert "(curve_points 5)" in teardrop_text
        _out, _err, code = convert(teardrop, work / "teardrop7_out.kicad_pcb", "7.0")
        assert code == 0
        teardrop7_text = (work / "teardrop7_out_V7.kicad_pcb").read_text(encoding="utf-8")
        assert "legacy_teardrops" not in teardrop7_text
        assert "(teardrops" not in teardrop7_text

        old = work / "old.kicad_pcb"
        old.write_text(
            '(kicad_pcb (version 20211014) (host pcbnew 5.0.2) (page A4) '
            '(layers (0 "F.Cu" signal)) (net 1 "N") '
            '(gr_arc (start 0 0) (end 1 0) (angle 90) (width 0.1) (layer "F.SilkS")) '
            '(gr_line (start 0 0) (end 1 1) (angle 45) (width 0.1) (layer "F.SilkS")) '
            '(segment (start 0 0) (end 1 0) (width 0.1) (layer "F.Cu") (net 1)))\n',
            encoding="utf-8",
        )
        _out, _err, code = convert(old, work / "old_up.kicad_pcb", "7.0")
        assert code == 0
        up_text = (work / "old_up_V7.kicad_pcb").read_text(encoding="utf-8")
        assert "(version 20221018)" in up_text
        assert '(paper "A4")' in up_text
        assert "(mid" in up_text
        assert "0.707106781" in up_text
        assert "(angle" not in up_text

        rect_net = work / "rect_net.kicad_pcb"
        rect_net.write_text(
            '(kicad_pcb (version 20240108) (generator "x") (paper "A4") '
            '(layers (0 "F.Cu" signal)) (net 0 "") (net 1 "N") '
            '(gr_rect (start 0 0) (end 1 1) (stroke (width 0.1) (type default)) '
            '(layer "F.Cu") (net 1)))\n',
            encoding="utf-8",
        )
        _out, _err, code = convert(rect_net, work / "rect_net_out.kicad_pcb", "7.0")
        assert code == 0
        rect_net_v7 = (work / "rect_net_out_V7.kicad_pcb").read_text(encoding="utf-8")
        assert "(version 20221018)" in rect_net_v7
        assert "(gr_rect" in rect_net_v7
        assert "(net 1)" not in rect_net_v7

        sym = work / "demo.kicad_sym"
        sym.write_text(
            '(kicad_symbol_lib (version 20251024) (generator "x") '
            '(symbol "Demo_Symbol" '
            '(property "Reference" "U" (at 0 0 0)) '
            '(property "Value" "Demo_Symbol" (at 0 -2 0)) '
            '(property "Description" "Demo description" (at 0 0 0)) '
            '(property "ki_description" "Demo description" (at 0 1 0)) '
            '(property "ki_keywords" "demo keywords" (at 0 0 0)) '
            '(property "Footprint" "Package:DIP" (at 2.54 3.81 0) (hide yes)) '
            '(property "Datasheet" "https://example.invalid/demo" (at 0 0 0)) '
            '(property "MPN" "ABC123" (at 1.27 2.54 90)) '
            '(exclude_from_sim yes) '
            '(pin_numbers hide) '
            '(pin_names (hide yes)) '
            '(rectangle (start -1 -1) (end 1 1) (stroke (width 0.15) (type default)) (fill (type background))) '
            '(rectangle (start 2 -1) (end 3 1) (stroke (width 0.15) (type default)) (fill (type outline))) '
            '(polyline (pts (xy -1 1) (xy 0 1.5) (xy 1 1)) (stroke (width 0.15) (type default)) (fill (type background))) '
            '(circle (center 0 -2) (radius 0.5) (stroke (width 0.15) (type default)) (fill (type background))) '
            '(arc (start -1 -2) (mid 0 -1) (end 1 -2) (stroke (width 0.15) (type default)) (fill (type background))) '
            '(text "TXT" (at 0 2.54 0) (effects (font (size 1.778 1.778) (bold yes) (italic yes)))) '
            '(pin input line (at -2 0 0) (length 2.54) (hide yes) (name "IN") (number "1")) '
            '(pin output inverted (at 2 0 180) (length 2.54) '
            '(name "OUT" (effects (font (size 1.778 1.778)))) '
            '(number "2" (effects (font (size 1.524 1.524))))) '
            '(symbol "Demo_Symbol_2_1" '
            '(pin passive line (at 0 2.54 270) (length 2.54) (name "U2") (number "3")))) '
            '(symbol "Demo_Alias" (extends "Demo_Symbol")))\n',
            encoding="utf-8",
        )
        _out, _err, code = convert(sym, work / "demo_sym6_out.kicad_sym", "6.0")
        assert code == 0
        sym6_text = (work / "demo_sym6_out_V6.kicad_sym").read_text(encoding="utf-8")
        sym6_compact = " ".join(sym6_text.split())
        assert "(version 20211014)" in sym6_text
        assert "exclude_from_sim" not in sym6_text
        assert "(hide yes)" not in sym6_text
        assert '(property "Reference" "U" (id 0)' in sym6_compact
        assert '(property "Value" "Demo_Symbol" (id 1)' in sym6_compact
        assert '(property "Datasheet" "https://example.invalid/demo" (id 3)' in sym6_compact
        assert '(property "ki_keywords" "demo keywords" (id 4)' in sym6_compact
        assert '(property "ki_description" "Demo description" (id 5)' in sym6_compact
        assert '(property "Description" "Demo description" (id 7)' in sym6_compact

        _out, _err, code = convert(sym, work / "demo_out.kicad_sym", "5.0")
        assert code == 0
        lib_text = (work / "demo_out_V5.lib").read_text(encoding="utf-8")
        dcm_text = (work / "demo_out_V5.dcm").read_text(encoding="utf-8")
        assert "DEF Demo_Symbol U 0 40 N N 2 F N" in lib_text
        assert 'ALIAS Demo_Alias' in lib_text
        assert 'F0 "U"' in lib_text
        assert 'F1 "Demo_Symbol"' in lib_text
        assert 'F2 "Package:DIP" 100 150 50 H I C CNN' in lib_text
        assert 'F3 "https://example.invalid/demo" 0 0 50 H V C CNN' in lib_text
        assert 'F4 "ABC123" 50 100 50 V V C CNN "MPN"' in lib_text
        assert "S -39 -39 39 39 1 1 6 f" in lib_text
        assert "S 79 -39 118 39 1 1 6 F" in lib_text
        assert "P 3 1 1 6 -39 39 0 59 39 39 f" in lib_text
        assert "C 0 -79 20 1 1 6 f" in lib_text
        assert "A 0 -39 56 0 0 1 1 6 f -39 -79 39 -79" in lib_text
        assert 'T 0 0 100 70 0 1 1 "TXT" Italic 1 C C' in lib_text
        assert "X IN 1 -79 0 100 R 50 50 1 1 I N" in lib_text
        assert "X OUT 2 79 0 100 L 70 60 1 1 O I" in lib_text
        assert "X U2 3 0 100 100 D 50 50 2 1 P" in lib_text
        assert "$CMP Demo_Symbol" in dcm_text
        assert "D Demo description" in dcm_text
        assert "K demo keywords" in dcm_text
        assert "F https://example.invalid/demo" in dcm_text

        _out, _err, code = convert(work / "demo_out_V5.lib", work / "demo_legacy_up.lib", "7.0")
        assert code == 0
        legacy_up = (work / "demo_legacy_up_V7.kicad_sym").read_text(encoding="utf-8")
        legacy_up_compact = " ".join(legacy_up.split())
        assert "(kicad_symbol_lib" in legacy_up
        assert "(version 20220914)" in legacy_up
        assert "(generator kicad-backport)" in legacy_up
        assert '"Demo_Symbol"' in legacy_up
        assert '"Demo_Symbol_2_1"' in legacy_up
        assert '"Demo_Alias"' in legacy_up
        assert '(extends "Demo_Symbol")' in legacy_up
        assert '"Reference"' in legacy_up and '"U"' in legacy_up
        assert '"Value"' in legacy_up and '"Demo_Symbol"' in legacy_up
        assert '"Footprint"' in legacy_up and '"Package:DIP"' in legacy_up
        assert '"Datasheet"' in legacy_up and '"https://example.invalid/demo"' in legacy_up
        assert '"ki_description"' in legacy_up and '"Demo description"' in legacy_up
        assert '"ki_keywords"' in legacy_up and '"demo keywords"' in legacy_up
        assert '"MPN"' in legacy_up and '"ABC123"' in legacy_up
        assert '(rectangle' in legacy_up
        assert '(text "TXT" (at 0 2.54 0)' in legacy_up_compact
        assert '(font (size 1.778 1.778) italic bold)' in legacy_up_compact
        assert '(pin' in legacy_up and 'input' in legacy_up and 'line' in legacy_up
        assert '(pin' in legacy_up and 'output' in legacy_up and 'inverted' in legacy_up
        assert '(hide yes)' not in legacy_up
        assert ' hide)' in legacy_up_compact or ' hide ' in legacy_up_compact
        assert '(name "OUT" (effects (font (size 1.778 1.778))))' in legacy_up_compact
        assert '(number "2" (effects (font (size 1.524 1.524))))' in legacy_up_compact
        assert '(fill (type background))' in legacy_up_compact
        assert '(fill (type outline))' in legacy_up_compact
        assert '(name "U2"' in legacy_up_compact
        assert '(name' in legacy_up and '"IN"' in legacy_up
        assert '(number' in legacy_up and '"1"' in legacy_up

        _out, _err, code = convert(work / "demo_out_V5.lib", work / "demo_legacy_up10.lib", "10.0")
        assert code == 0
        legacy_up10 = (work / "demo_legacy_up10_V10.kicad_sym").read_text(encoding="utf-8")
        legacy_up10_compact = " ".join(legacy_up10.split())
        assert "(version 20251024)" in legacy_up10
        assert "(font (size 1.778 1.778) (italic yes) (bold yes))" in legacy_up10_compact

        text_angle_lib = work / "text_angle.lib"
        text_angle_lib.write_text(
            "EESchema-LIBRARY Version 2.4\n"
            "#encoding utf-8\n"
            "DEF TextAngle U 0 40 Y Y 1 F N\n"
            "F0 \"U\" 0 0 50 H V C CNN\n"
            "F1 \"TextAngle\" 0 100 50 H V C CNN\n"
            "DRAW\n"
            "T 900 50 50 50 0 1 1 \"ROT\" Normal 0 C C\n"
            "ENDDRAW\n"
            "ENDDEF\n"
            "#\n#End Library\n",
            encoding="utf-8",
        )
        _out, _err, code = convert(text_angle_lib, work / "text_angle_up.lib", "7.0")
        assert code == 0
        text_angle_up = (work / "text_angle_up_V7.kicad_sym").read_text(encoding="utf-8")
        text_angle_up_compact = " ".join(text_angle_up.split())
        assert '(text "ROT" (at 1.27 1.27 900)' in text_angle_up_compact

        (work / "demo.lib").write_text(lib_text, encoding="utf-8")
        cache_sch = work / "cache.sch"
        cache_sch.write_text(
            "EESchema Schematic File Version 4\n"
            "LIBS:demo\n"
            "EELAYER 30 0\n"
            "EELAYER END\n"
            "$Descr A4 11693 8268\n"
            "$EndDescr\n"
            "$Comp\n"
            "L Demo_Symbol U1\n"
            "U 1 1 ABCD1234\n"
            "P 100 100\n"
            "F 0 \"U1\" H 100 100 50  0000 C CNN\n"
            "F 1 \"Demo_Symbol\" H 100 200 50  0000 C CNN\n"
            "\t1    100 100\n"
            "\t1    0    0    -1\n"
            "$EndComp\n"
            "$EndSCHEMATC\n",
            encoding="utf-8",
        )
        _out, _err, code = convert(cache_sch, work / "cache_up.sch", "7.0")
        assert code == 0
        cache_up = (work / "cache_up_V7.kicad_sch").read_text(encoding="utf-8")
        cache_up_compact = " ".join(cache_up.split())
        assert '(lib_id "demo:Demo_Symbol")' in cache_up
        assert '(pin "1" (uuid' not in cache_up_compact
        _out, _err, code = convert(cache_sch, work / "cache_up6.sch", "6.0")
        assert code == 0
        cache_up6 = (work / "cache_up6_V6.kicad_sch").read_text(encoding="utf-8")
        cache_up6_compact = " ".join(cache_up6.split())
        assert '(lib_id "demo:Demo_Symbol")' in cache_up6
        assert '(pin "1" (uuid' in cache_up6_compact

        ar_sch = work / "ar_ref.sch"
        ar_sch.write_text(
            "EESchema Schematic File Version 4\n"
            "LIBS:demo\n"
            "EELAYER 30 0\n"
            "EELAYER END\n"
            "$Descr A4 11693 8268\n"
            "$EndDescr\n"
            "$Comp\n"
            "L Demo_Symbol U?A\n"
            "U 1 1 ABCD9999\n"
            "P 100 100\n"
            "AR Path=\"/5F00\" Ref=\"U9\"  Part=\"1\"\n"
            "F 0 \"U?A\" H 100 100 50  0000 C CNN\n"
            "F 1 \"Demo_Symbol\" H 100 200 50  0000 C CNN\n"
            "\t1    100 100\n"
            "\t1    0    0    -1\n"
            "$EndComp\n"
            "$EndSCHEMATC\n",
            encoding="utf-8",
        )
        _out, _err, code = convert(ar_sch, work / "ar_ref_up.sch", "7.0")
        assert code == 0
        ar_up = (work / "ar_ref_up_V7.kicad_sch").read_text(encoding="utf-8")
        assert re.search(r'\(lib_id "demo:Demo_Symbol"\)[\s\S]*?\(property\s+"Reference"\s+"U9"', ar_up)
        assert '"U?A"' not in ar_up

        power_lib = work / "power.lib"
        power_lib.write_text(
            "EESchema-LIBRARY Version 2.4\n"
            "#encoding utf-8\n"
            "DEF +5V #PWR 0 0 Y Y 1 F P\n"
            "F0 \"#PWR\" 0 -100 50 H I C CNN\n"
            "F1 \"+5V\" 0 100 50 H V C CNN\n"
            "DRAW\n"
            "X +5V 1 0 0 0 U 50 50 1 1 W N\n"
            "ENDDRAW\n"
            "ENDDEF\n"
            "#\n#End Library\n",
            encoding="utf-8",
        )
        power_sch = work / "power.sch"
        power_sch.write_text(
            "EESchema Schematic File Version 4\n"
            "LIBS:power\n"
            "EELAYER 30 0\n"
            "EELAYER END\n"
            "$Descr A4 11693 8268\n"
            "$EndDescr\n"
            "$Comp\n"
            "L +5V #U?\n"
            "U 1 1 ABCD5555\n"
            "P 100 100\n"
            "F 0 \"#U?\" H 100 100 50  0001 C CNN\n"
            "F 1 \"+5V\" H 100 200 50  0000 C CNN\n"
            "\t1    100 100\n"
            "\t1    0    0    -1\n"
            "$EndComp\n"
            "$EndSCHEMATC\n",
            encoding="utf-8",
        )
        _out, _err, code = convert(power_sch, work / "power_up.sch", "7.0")
        assert code == 0
        power_up = (work / "power_up_V7.kicad_sch").read_text(encoding="utf-8")
        assert re.search(r'\(lib_id "power:\+5V"\)[\s\S]*?\(property\s+"Reference"\s+"#PWR"', power_up)
        assert '"#U?"' not in power_up

        dcm_only = work / "only.dcm"
        dcm_only.write_text(
            "EESchema-DOCLIB  Version 2.0\n"
            "$CMP DocOnly\n"
            "D Documentation only symbol\n"
            "K doc only\n"
            "F https://example.invalid/doc-only\n"
            "$ENDCMP\n"
            "#\n#End Doc Library\n",
            encoding="utf-8",
        )
        _out, _err, code = convert(dcm_only, work / "only_out.dcm", "7.0")
        assert code == 0
        dcm_only_up = (work / "only_out_V7.kicad_sym").read_text(encoding="utf-8")
        assert "(generator kicad-backport)" in dcm_only_up
        assert '"DocOnly"' in dcm_only_up
        assert '"ki_description"' in dcm_only_up and '"Documentation only symbol"' in dcm_only_up
        assert '"ki_keywords"' in dcm_only_up and '"doc only"' in dcm_only_up
        assert '"Datasheet"' in dcm_only_up and '"https://example.invalid/doc-only"' in dcm_only_up

        special_lib = work / "special.lib"
        special_lib.write_text(
            "EESchema-LIBRARY Version 2.4\n"
            "#encoding utf-8\n"
            "DEF CP8 C? 0 40 Y Y 1 F N\n"
            "F0 \"C?\" 0 0 50 H V C CNN\n"
            "F1 \"CP8\" 0 -100 50 H V C CNN\n"
            "DRAW\n"
            "X ~ 1 0 0 100 R 50 50 1 1 P\n"
            "ENDDRAW\n"
            "ENDDEF\n"
            "DEF HIDE_NUM U 0 40 N Y 1 F N\n"
            "F0 \"U\" 0 0 50 H V C CNN\n"
            "F1 \"HIDE_NUM\" 0 -100 50 H V C CNN\n"
            "DRAW\n"
            "X IN 1 -200 0 100 R 50 50 1 1 I\n"
            "ENDDRAW\n"
            "ENDDEF\n"
            "DEF HIDE_NAME U 0 40 Y N 1 F N\n"
            "F0 \"U\" 0 0 50 H V C CNN\n"
            "F1 \"HIDE_NAME\" 0 -100 50 H V C CNN\n"
            "DRAW\n"
            "X OUT 1 200 0 100 L 50 50 1 1 O\n"
            "ENDDRAW\n"
            "ENDDEF\n"
            "DEF PWR_ROT #PWR 0 0 Y Y 1 F P\n"
            "F0 \"#PWR\" 0 -150 50 H I C CNN\n"
            "F1 \"PWR_ROT\" 0 150 50 V V C CNN\n"
            "DRAW\n"
            "X PWR 1 0 0 0 U 50 50 1 1 W N\n"
            "ENDDRAW\n"
            "ENDDEF\n"
            "#End Library\n",
            encoding="utf-8",
        )
        _out, _err, code = convert(special_lib, work / "special_out.lib", "6.0")
        assert code == 0
        special_up = (work / "special_out_V6.kicad_sym").read_text(encoding="utf-8")
        assert re.search(r'"CP8"[\s\S]*?\(property\s+"Reference"\s+"C"\s', special_up)
        assert not re.search(r'\(property\s+"Reference"\s+"C\?"', special_up)
        assert "(pin_numbers hide)" in special_up
        assert "(pin_names hide)" in special_up
        assert "(pin_numbers\n      (hide" not in special_up
        assert "(pin_names\n      (hide" not in special_up
        assert re.search(r'"PWR_ROT"[\s\S]*?\(property\s+"Reference"\s+"#PWR"', special_up)
        assert re.search(r'"PWR_ROT"[\s\S]*?\(property\s+"Value"\s+"PWR_ROT"\s+\(at 0 3\.81 90\)', special_up)

        sch = work / "demo.kicad_sch"
        sch.write_text(
            '(kicad_sch (version 20260306) (generator "x") (paper "A4") '
            '(title_block (title "Demo") (date "2026-06-07") (rev "A") '
            '(company "AskStar") (comment 1 "Checked")) '
            '(wire (pts (xy 0 0) (xy 10 0))) '
            '(bus (pts (xy 0 2.54) (xy 10 2.54))) '
            '(bus_entry (at 10 2.54) (size 2.54 -2.54)) '
            '(polyline (pts (xy 0 7.62) (xy 5.08 7.62) (xy 5.08 10.16)) '
            '(stroke (width 0.15) (type default)) '
            '(uuid "66666666-6666-6666-6666-666666666666")) '
            '(rectangle (start 6.35 7.62) (end 8.89 8.89) '
            '(stroke (width 0.15) (type default)) '
            '(uuid "77777777-7777-7777-7777-777777777777")) '
            '(circle (center 12.7 7.62) (radius 1.27) '
            '(stroke (width 0.15) (type default)) '
            '(uuid "88888888-8888-8888-8888-888888888888")) '
            '(arc (start 15.24 7.62) (mid 16.51 8.89) (end 17.78 7.62) '
            '(stroke (width 0.15) (type default)) '
            '(uuid "99999999-0000-0000-0000-999999999999")) '
            '(bezier (pts (xy 27.94 7.62) (xy 29.21 8.89) (xy 30.48 6.35) (xy 31.75 7.62)) '
            '(stroke (width 0.15) (type default)) '
            '(uuid "99999999-1111-1111-1111-999999999999")) '
            '(junction (at 5 0)) '
            '(no_connect (at 7.62 0)) '
            '(text "Linked" (at 0 5 0) (effects (font (size 1.778 1.778))) '
            '(uuid "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa") (hyperlink "https://example.invalid/text")) '
            '(text_box "Boxed" (at 20 7.62 0) (size 5.08 2.54) '
            '(stroke (width 0.15) (type default)) '
            '(uuid "aaaaaaaa-bbbb-bbbb-bbbb-aaaaaaaaaaaa")) '
            '(label "NET_A" (at 2.54 0 0)) '
            '(global_label "GLOB" (shape input) (at 2.54 2.54 0) '
            '(effects (font (size 1.524 1.524))) (hyperlink "https://example.invalid/global")) '
            '(directive_label "NC" (at 5 5 0) (uuid "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb") (hyperlink "https://example.invalid/netclass")) '
            '(lib_symbols (symbol "demo:Demo_Symbol" (pin_names (hide yes)) '
            '(pin input line (at 0 0 0) (length 2.54) (hide yes) (alternate "ALT" input line) '
            '(name "IN") (number "1")))) '
            '(sheet (at 20 20) (size 10 8) '
            '(property "Sheetname" "Child" (id 9) (at 20 20 0) (effects (font (size 1.778 1.778)))) '
            '(property "Sheetfile" "child.kicad_sch" (at 20 22 0) (effects (font (size 1.524 1.524)))) '
            '(uuid "12345678-1234-1234-1234-123456789abc") '
            '(pin "IN" (type input) (at 20 21 180) (effects (font (size 1.016 1.016))))) '
            '(symbol (lib_id "demo:Demo_Symbol") (at 10 10 0) '
            '(uuid "87654321-1234-1234-1234-123456789abc") '
            '(dnp yes) '
            '(property "Reference" "U1" (at 10 10 0) (effects (font (size 1.778 1.778)))) '
            '(property "Value" "Demo_Symbol" (at 10 12 0) (effects (font (size 1.524 1.524)))) '
            '(property "Footprint" "Package:DIP" (at 10 14 0) (effects (font (size 1.27 1.27)) hide)) '
            '(property "Datasheet" "https://example.invalid/demo" (at 10 16 0)) '
            '(property "ki_description" "Demo description" (at 10 18 0)) '
            '(property "Custom" "C" (at 10 20 0) (effects (font (size 1.016 1.016)) hide)) '
            '(pin "1" (uuid "99999999-9999-9999-9999-999999999999")) '
            '(instances (project "demo" (path "/87654321-1234-1234-1234-123456789abc" '
            '(reference "U1") (unit 1) (value "Demo_Symbol") (footprint "Package:DIP"))))) '
            '(symbol (lib_id "demo:Demo_Symbol") (at 20 10 90) '
            '(uuid "11111111-1111-1111-1111-111111111111") '
            '(property "Reference" "C90" (at 20 10 90)) '
            '(property "Value" "90" (at 20 12 90))) '
            '(symbol (lib_id "demo:Demo_Symbol") (at 30 10 180) '
            '(uuid "22222222-2222-2222-2222-222222222222") '
            '(property "Reference" "C180" (at 30 10 180)) '
            '(property "Value" "180" (at 30 12 180))) '
            '(symbol (lib_id "demo:Demo_Symbol") (at 40 10 270) '
            '(uuid "33333333-3333-3333-3333-333333333333") '
            '(property "Reference" "C270" (at 40 10 270)) '
            '(property "Value" "270" (at 40 12 270))) '
            '(symbol (lib_id "demo:Demo_Symbol") (at 50 10 90) (mirror x) '
            '(uuid "44444444-4444-4444-4444-444444444444") '
            '(property "Reference" "C90X" (at 50 10 90)) '
            '(property "Value" "90X" (at 50 12 90))) '
            '(symbol (lib_id "demo:Demo_Symbol") (at 60 10 0) (mirror y) '
            '(uuid "55555555-5555-5555-5555-555555555555") '
            '(property "Reference" "C0Y" (at 60 10 0)) '
            '(property "Value" "0Y" (at 60 12 0))) '
            '(sheet_instances (path "/" (page "1"))) '
            '(symbol_instances))\n',
            encoding="utf-8",
        )
        _out, _err, code = convert(sch, work / "demo_sch6_out.kicad_sch", "6.0")
        assert code == 0
        sch6_text = (work / "demo_sch6_out_V6.kicad_sch").read_text(encoding="utf-8")
        sch6_compact = " ".join(sch6_text.split())
        assert "(version 20211123)" in sch6_text
        assert "(netclass_flag" in sch6_text
        assert "(directive_label" not in sch6_text
        assert "hyperlink" not in sch6_text
        assert "dnp" not in sch6_text
        assert "alternate" not in sch6_text
        assert "(hide yes)" not in sch6_text
        assert "(pin_names hide)" in sch6_text
        assert '(uuid "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")' not in sch6_text
        assert "(uuid aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa)" in sch6_text
        assert '(uuid "87654321-1234-1234-1234-123456789abc")' not in sch6_text
        assert "(uuid 87654321-1234-1234-1234-123456789abc)" in sch6_text
        assert '(property "Sheet name" "Child" (id 0)' in sch6_compact
        assert '(property "Sheet file" "child.kicad_sch" (id 1)' in sch6_compact
        assert '(property "Reference" "U1" (id 0)' in sch6_compact
        assert '(property "Value" "Demo_Symbol" (id 1)' in sch6_compact
        assert '(property "Footprint" "Package:DIP" (id 2)' in sch6_compact
        assert '(property "Datasheet" "https://example.invalid/demo" (id 3)' in sch6_compact
        assert '(property "ki_description" "Demo description" (id 5)' in sch6_compact
        assert '(property "Custom" "C" (id 7)' in sch6_compact
        assert "(instances" not in sch6_text
        assert "(symbol_instances" in sch6_text
        assert '(pin "1" (uuid 99999999-9999-9999-9999-999999999999))' in sch6_compact
        assert '(path "/87654321-1234-1234-1234-123456789abc"' in sch6_compact

        _out, _err, code = convert(sch, work / "demo_sch7_out.kicad_sch", "7.0")
        assert code == 0
        sch7_text = (work / "demo_sch7_out_V7.kicad_sch").read_text(encoding="utf-8")
        sch7_compact = " ".join(sch7_text.split())
        assert '(pin "1" (uuid 99999999-9999-9999-9999-999999999999))' not in sch7_compact
        assert "(symbol_instances" in sch7_text

        hidden_power_sch = work / "hidden_power.kicad_sch"
        hidden_power_sch.write_text(
            '(kicad_sch (version 20260306) (generator "x") (paper "A4") '
            '(uuid "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee") '
            '(symbol (lib_id "power:+5V") (at 0 0 0) '
            '(uuid "99999999-9999-9999-9999-999999999999") '
            '(property "Reference" "#U?" (at 0 0 0)) '
            '(property "Value" "+5V" (at 0 1 0)) '
            '(instances (project "demo" '
            '(path "/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/99999999-9999-9999-9999-999999999999" '
            '(reference "#U5") (unit 2) (value "+5V") (footprint "Power:Flag"))))) '
            '(sheet_instances (path "/" (page "1"))) '
            '(symbol_instances))\n',
            encoding="utf-8",
        )
        _out, _err, code = convert(hidden_power_sch, work / "hidden_power_out.kicad_sch", "6.0")
        assert code == 0
        hidden_power_out = (work / "hidden_power_out_V6.kicad_sch").read_text(encoding="utf-8")
        hidden_power_out_compact = " ".join(hidden_power_out.split())
        assert '(symbol_instances (path "/99999999-9999-9999-9999-999999999999" (reference "#PWR5") (unit 2) (value "+5V") (footprint "Power:Flag")))' in hidden_power_out_compact

        _out, _err, code = convert(sch, work / "demo_sch_out.kicad_sch", "5.0")
        assert code == 0
        sch_text = (work / "demo_sch_out_V5.sch").read_text(encoding="utf-8")
        assert "EESchema Schematic File Version 4" in sch_text
        assert "LIBS:demo" in sch_text
        assert 'Title "Demo"' in sch_text
        assert "Wire Wire Line" in sch_text
        assert "Wire Bus Line" in sch_text
        assert "Wire Notes Line" in sch_text
        assert sch_text.count("Wire Notes Line") >= 50
        assert "\t0 300 200 300" in sch_text
        assert "\t200 300 200 400" in sch_text
        assert "\t250 300 350 300" in sch_text
        assert "\t787 300 987 300" in sch_text
        assert "Entry Wire Line" in sch_text
        assert "Connection ~" in sch_text
        assert "NoConn ~" in sch_text
        assert "Text Label" in sch_text
        assert "Text GLabel" in sch_text
        assert "Text Notes 0 197 0 70 ~ 0\nLinked" in sch_text
        assert "Text GLabel 100 100 0 60 Input ~ 0\nGLOB" in sch_text
        assert "Text Notes" in sch_text and "Boxed" in sch_text
        assert "\nNC\n" in sch_text
        assert "$Sheet" in sch_text
        assert 'F0 "Child" 70' in sch_text
        assert 'F1 "child.sch" 60' in sch_text
        assert 'F2 "IN" I L 787 827 40' in sch_text
        assert "$Comp" in sch_text
        assert "L demo:Demo_Symbol U1" in sch_text
        assert "F 0 \"U1\"" in sch_text
        assert 'F 0 "U1" H 394 394 70  0000 C CNN' in sch_text
        assert 'F 1 "Demo_Symbol" H 394 472 60  0000 C CNN' in sch_text
        assert 'F 2 "Package:DIP" H 394 551 50  0001 C CNN' in sch_text
        assert 'F 4 "C" H 394 787 40  0001 C CNN "Custom"' in sch_text
        assert "L demo:Demo_Symbol C90" in sch_text
        assert "\t0    -1    -1    0\n$EndComp" in sch_text
        assert "L demo:Demo_Symbol C180" in sch_text
        assert "\t-1    0    0    1\n$EndComp" in sch_text
        assert "L demo:Demo_Symbol C270" in sch_text
        assert "\t0    1    1    0\n$EndComp" in sch_text
        assert "L demo:Demo_Symbol C90X" in sch_text
        assert "\t0    -1    1    0\n$EndComp" in sch_text
        assert "L demo:Demo_Symbol C0Y" in sch_text
        assert "\t-1    0    0    -1\n$EndComp" in sch_text

        _out, _err, code = convert(work / "demo_sch_out_V5.sch", work / "demo_sch_legacy_up.sch", "7.0")
        assert code == 0
        sch_up = (work / "demo_sch_legacy_up_V7.kicad_sch").read_text(encoding="utf-8")
        sch_up_compact = " ".join(sch_up.split())
        assert "(generator kicad-backport)" in sch_up
        assert "(kicad_sch" in sch_up
        assert "(version 20230121)" in sch_up
        assert "(title_block" in sch_up
        assert '"Demo"' in sch_up
        assert "(wire" in sch_up
        assert "(bus" in sch_up
        assert "(polyline" in sch_up
        assert "(bus_entry" in sch_up
        assert "(junction" in sch_up
        assert "(no_connect" in sch_up
        assert "(label" in sch_up and '"NET_A"' in sch_up
        assert "(global_label" in sch_up and '"GLOB"' in sch_up
        assert '(global_label "GLOB" (shape input)' in sch_up_compact
        assert '(text "Linked" (at 0 5.0038 0) (effects (font (size 1.778 1.778)))' in sch_up_compact
        assert '(global_label "GLOB" (shape input) (at 2.54 2.54 0) (effects (font (size 1.524 1.524)))' in sch_up_compact
        assert '(property "Reference" "U1" (at 10.0076 10.0076 0) (effects (font (size 1.778 1.778))))' in sch_up_compact
        assert '(property "Value" "Demo_Symbol" (at 10.0076 11.9888 0) (effects (font (size 1.524 1.524))))' in sch_up_compact
        assert '(property "Footprint" "Package:DIP" (at 10.0076 13.9954 0) (effects (font (size 1.27 1.27)) hide))' in sch_up_compact
        assert '(property "Custom" "C" (at 10.0076 19.9898 0) (effects (font (size 1.016 1.016)) hide))' in sch_up_compact
        assert "(sheet" in sch_up and '"Child"' in sch_up and '"child.kicad_sch"' in sch_up
        assert '(property "Sheet name" "Child" (at 19.9898 19.9898 0) (effects (font (size 1.778 1.778))))' in sch_up_compact
        assert '(property "Sheet file" "child.kicad_sch" (at 19.9898 19.9898 0) (effects (font (size 1.524 1.524))))' in sch_up_compact
        assert '(pin "IN" (type input) (at 19.9898 21.0058 180) (effects (font (size 1.016 1.016)))' in sch_up_compact
        assert "(symbol" in sch_up and '"demo:Demo_Symbol"' in sch_up
        assert "(symbol_instances" in sch_up
        assert "(sheet_instances" in sch_up
        assert re.search(r'\(symbol\s+\(lib_id "demo:Demo_Symbol"\)\s+\(at [^)]* 90\)[\s\S]*?\(property\s+"Reference"\s+"C90"', sch_up)
        assert re.search(r'\(symbol\s+\(lib_id "demo:Demo_Symbol"\)\s+\(at [^)]* 180\)[\s\S]*?\(property\s+"Reference"\s+"C180"', sch_up)
        assert re.search(r'\(symbol\s+\(lib_id "demo:Demo_Symbol"\)\s+\(at [^)]* 270\)[\s\S]*?\(property\s+"Reference"\s+"C270"', sch_up)
        assert re.search(r'\(symbol\s+\(lib_id "demo:Demo_Symbol"\)\s+\(at [^)]* 90\)\s+\(mirror x\)[\s\S]*?\(property\s+"Reference"\s+"C90X"', sch_up)
        assert re.search(r'\(symbol\s+\(lib_id "demo:Demo_Symbol"\)\s+\(at [^)]* 180\)\s+\(mirror x\)[\s\S]*?\(property\s+"Reference"\s+"C0Y"', sch_up)

        project = work / "project"
        project.mkdir()
        (project / "Library.pretty").mkdir()
        (project / "Library.pretty" / "LocalPart.kicad_mod").write_text(
            '(footprint "LocalPart" (version 20211014) (generator "x") (layer "F.Cu"))\n',
            encoding="utf-8",
        )
        (project / "demo.kicad_pro").write_text('{"meta": {"version": 1}}\n', encoding="utf-8")
        (project / "demo.kicad_prl").write_text(
            '{"board": {"visible_items": ["vias", "tracks", "zones"], '
            '"visible_layers": "0000000f_ffffffff"}}\n',
            encoding="utf-8",
        )
        (project / "sym-lib-table").write_text(
            '(sym_lib_table (version 7) '
            '(lib (name "demo") (type "KiCad") (uri "${KIPRJMOD}/demo.kicad_sym") '
            '(options "") (descr "")))\n',
            encoding="utf-8",
        )
        (project / "fp-lib-table").write_text('(fp_lib_table (version 7))\n', encoding="utf-8")
        (project / "demo.kicad_sym").write_text(sym.read_text(encoding="utf-8"), encoding="utf-8")
        (project / "demo.kicad_sch").write_text(sch.read_text(encoding="utf-8"), encoding="utf-8")
        (project / "child.kicad_sch").write_text(
            '(kicad_sch (version 20260306) (generator "x") (paper "A4") '
            '(symbol (lib_id "demo:Demo_Symbol") (at 5 5 0) '
            '(uuid "22222222-2222-2222-2222-222222222222") '
            '(property "Reference" "U2" (at 5 5 0)) '
            '(property "Value" "Demo_Symbol" (at 5 7 0))) '
            '(sheet_instances (path "/" (page "1"))) '
            '(symbol_instances))\n',
            encoding="utf-8",
        )
        (project / "demo.kicad_pcb").write_text(
            '(kicad_pcb (version 20260603) (generator "x") '
            '(paper "A4") (layers (0 "F.Cu" signal)) '
            '(footprint "Local:LocalPart" (layer "F.Cu")))\n',
            encoding="utf-8",
        )
        _out, _err, code = convert(project, work / "project_out", "5.0")
        assert code == 0
        project_v5 = work / "project_out_V5"
        assert (project_v5 / "demo.lib").exists()
        assert not (project_v5 / "demo.kicad_sym").exists()
        assert (project_v5 / "demo.pro").exists()
        assert not (project_v5 / "demo.kicad_pro").exists()
        project_pro_text = (project_v5 / "demo.pro").read_text(encoding="utf-8")
        assert "last_client=kicad-backport" in project_pro_text
        assert "LibName1=demo" in project_pro_text
        sym_table = (project_v5 / "sym-lib-table").read_text(encoding="utf-8")
        assert '(type "Legacy")' in sym_table
        assert "demo.lib" in sym_table
        assert "(version" not in sym_table
        fp_table = (project_v5 / "fp-lib-table").read_text(encoding="utf-8")
        assert '(name "Local")' in fp_table
        assert "${KIPRJMOD}/Library.pretty" in fp_table

        legacy_project = work / "legacy_project"
        legacy_project.mkdir()
        (legacy_project / "demo.pro").write_text(
            "update=2\n"
            "version=1\n"
            "last_client=eeschema\n"
            "LibDir=legacy_libs\n"
            "NetIExt=netx\n"
            "CmpExt=.cmpx\n"
            "PageLayoutDescrFile=page.kicad_wks\n"
            "PlotDirectoryName=plots\n"
            "SubpartIdSeparator=1\n"
            "SubpartFirstId=66\n"
            "LibName1=demo\n"
            "LibName2=power\n",
            encoding="utf-8",
        )
        (legacy_project / "demo.lib").write_text(lib_text, encoding="utf-8")
        (legacy_project / "demo.dcm").write_text(dcm_text, encoding="utf-8")
        (legacy_project / "demo.sch").write_text(sch_text, encoding="utf-8")
        (legacy_project / "child.sch").write_text(
            "EESchema Schematic File Version 4\n"
            "EELAYER 30 0\n"
            "EELAYER END\n"
            "$Descr A4 11693 8268\n"
            "$EndDescr\n"
            "$Comp\n"
            "L demo:Demo_Symbol U2\n"
            "U 1 1 22222222\n"
            "P 200 200\n"
            "F 0 \"U2\" H 200 200 50  0000 C CNN\n"
            "F 1 \"Demo_Symbol\" H 200 300 50  0000 C CNN\n"
            "\t1    200 200\n"
            "\t1    0    0    -1\n"
            "$EndComp\n"
            "$EndSCHEMATC\n",
            encoding="utf-8",
        )
        _out, _err, code = convert(legacy_project, work / "legacy_project_out", "7.0")
        assert code == 0
        legacy_project_v7 = work / "legacy_project_out_V7"
        assert (legacy_project_v7 / "demo.kicad_pro").exists()
        assert (legacy_project_v7 / "demo.kicad_sym").exists()
        assert (legacy_project_v7 / "demo.kicad_sch").exists()
        assert (legacy_project_v7 / "sym-lib-table").exists()
        assert not (legacy_project_v7 / "demo.dcm").exists()
        legacy_project_sym_table = (legacy_project_v7 / "sym-lib-table").read_text(encoding="utf-8")
        assert '(version 7)' in legacy_project_sym_table
        assert '(name "demo")' in legacy_project_sym_table
        assert '(type "KiCad")' in legacy_project_sym_table
        assert '${KIPRJMOD}/demo.kicad_sym' in legacy_project_sym_table
        legacy_project_json = (legacy_project_v7 / "demo.kicad_pro").read_text(encoding="utf-8")
        assert '"legacy_symbol_libraries"' in legacy_project_json
        assert '"demo"' in legacy_project_json and '"power"' in legacy_project_json
        assert '"project_settings"' in legacy_project_json
        assert '"last_client": "eeschema"' in legacy_project_json
        assert '"NetIExt": "netx"' in legacy_project_json
        legacy_project_sym = (legacy_project_v7 / "demo.kicad_sym").read_text(encoding="utf-8")
        assert '"Demo_Alias"' in legacy_project_sym
        assert '"ki_description"' in legacy_project_sym and '"Demo description"' in legacy_project_sym
        legacy_project_sch = (legacy_project_v7 / "demo.kicad_sch").read_text(encoding="utf-8")
        assert "(symbol_instances" in legacy_project_sch
        assert '"demo:Demo_Symbol"' in legacy_project_sch
        assert "(lib_symbols" in legacy_project_sch
        assert '"U2"' in legacy_project_sch

        _out, _err, code = convert(project, work / "project_out7", "7.0")
        assert code == 0
        project_v7 = work / "project_out7_V7"
        assert (project_v7 / "sym-lib-table").exists()
        project_v7_sym_table = (project_v7 / "sym-lib-table").read_text(encoding="utf-8")
        assert '(name "demo")' in project_v7_sym_table
        assert '${KIPRJMOD}/demo.kicad_sym' in project_v7_sym_table
        project_v7_sch = (project_v7 / "demo.kicad_sch").read_text(encoding="utf-8")
        assert "(lib_symbols" in project_v7_sch
        assert '"demo:Demo_Symbol"' in project_v7_sch
        assert "/12345678-1234-1234-1234-123456789abc/22222222-2222-2222-2222-222222222222" in project_v7_sch
        assert '"U2"' in project_v7_sch
        prl = (work / "project_out7_V7" / "demo.kicad_prl").read_text(encoding="utf-8")
        assert '"version": 3' in prl
        assert '"visible_layers": "000000f_ffffffff"' in prl
        print("compat smoke ok")
        return 0
    finally:
        shutil.rmtree(str(work), ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
