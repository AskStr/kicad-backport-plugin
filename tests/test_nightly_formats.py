"""Regression contract for KiCad master 5ba95b2054 (2026-09-17 UTC)."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from plugin import backport_core as core


BOARD = '(kicad_pcb (version {version}) (generator "pcbnew") (layers (0 "F.Cu" signal) (2 "B.Cu" signal) (37 "F.SilkS" user) (36 "Dwgs.User" user "User.Drawings")) {items})'
LINE = '(gr_line (start 10 10) (end 20 10) (stroke (width 0.2) (type solid)) (layer "F.Cu") (uuid "11111111-1111-4111-8111-111111111111") {ending})'


CHART_ID = '22222222-2222-4222-8222-222222222222'
MAP_ID = '33333333-3333-4333-8333-333333333333'
CELL_ID = '44444444-4444-4444-8444-444444444444'
DRILL_CHART = r'''(drill_chart
 (uuid "22222222-2222-4222-8222-222222222222") (locked yes) (layer "Dwgs.User")
 (filter (plated yes) (npth yes) (vias yes) (slots yes) (backdrill no) (castellated yes))
 (units mm) (precision 3) (totals yes)
 (column (id symbol) (name "Mark") (justify center) (width 10))
 (row_shapes (column 0) (shape 0 2)) (row_keys (key 0 "plated-0.3"))
 (column_count 1)
 (border (external yes) (header yes) (stroke (width 0.1) (type solid)))
 (separators (rows yes) (cols yes) (stroke (width 0.1) (type solid)))
 (column_widths 10) (row_heights 5)
 (cells (table_cell "0.300 mm / 2 holes" (start 10 10) (end 20 15)
   (margins 0.5 0.5 0.5 0.5) (span 1 1) (layer "Dwgs.User")
   (effects (font (size 1 1) (thickness 0.15)))
   (uuid "44444444-4444-4444-8444-444444444444")))
 (custom_property "audit" "keep-on-recent-targets"))'''
DRILL_MAP = '''(drill_map (uuid "33333333-3333-4333-8333-333333333333")
 (locked yes) (layer "Dwgs.User") (offset 30 0) (size 2)
 (span "F.Cu" "B.Cu" npth) (outline_slots yes) (guide_cross yes))'''
DRILL_PROFILE = '''(setup (drill_symbol_profile (name "Fab") (group_by size plating)
 (default_marks shapes) (size 2) (width 0.15) (freeze_assignments yes)
 (assignment (key "plated-0.3") (mark shape 2) (descr "small holes"))))'''
DRILL_VIA = '''(via (at 5 5) (size 0.6) (drill 0.3) (layers "F.Cu" "B.Cu")
 (uuid "55555555-5555-4555-8555-555555555555"))'''
DRILL_GROUP = '''(group "Drilling" (uuid "66666666-6666-4666-8666-666666666666")
 (members "22222222-2222-4222-8222-222222222222" "33333333-3333-4333-8333-333333333333"
 "55555555-5555-4555-8555-555555555555"))'''
DRILL_ITEMS = DRILL_PROFILE + DRILL_CHART + DRILL_MAP + DRILL_VIA + DRILL_GROUP


class NightlyFormatsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='backport_nightly_')
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.serial = 0

    def convert(self, text, extension='.kicad_pcb', target='10.0'):
        self.serial += 1
        source = self.work / ('source%d' % self.serial + extension)
        output = self.work / ('output%d' % self.serial + extension)
        report = self.work / ('report%d.json' % self.serial)
        source.write_text(text, encoding='utf-8')
        stdout, stderr, code = core.convert(source, output, target, report)
        self.assertEqual(code, 0, stdout + stderr)
        self.assertEqual(source.read_text(encoding='utf-8'), text, 'source must not be modified')
        result = core.versioned_output_path(output, target)
        return result.read_text(encoding='utf-8'), json.loads(report.read_text(encoding='utf-8'))['files'][0], result

    def board(self, items, version=20260831, target='10.0'):
        return self.convert(BOARD.format(version=version, items=items), target=target)

    def warning(self, report, fragment):
        self.assertTrue(any(fragment in w for w in report.get('warnings', [])), report)

    def test_profile_and_keep_latest(self):
        for kind, version in [('board', '20260901'), ('footprint', '20260901'), ('schematic', '20260830'), ('symbol-library', '20260830')]:
            self.assertEqual(core.resolve_target_version(kind, '10.99'), version)
        text = BOARD.format(version=20260901, items=LINE.format(ending='(end_shape arrow) (custom_property "key" "value")'))
        out, report, _ = self.convert(text, target='10.99')
        self.assertEqual(out, text)
        self.assertFalse(report['changed'])
        for date in ['20260710', '20260803', '20260816', '20260818', '20260826', '20260828', '20260830', '20260831', '20260901']:
            self.assertIn(date, core.DEVELOPMENT_FILE_TARGETS)
            self.assertEqual(core.resolve_target_version('design-rules', date), '1')

    def test_drill_objects_preserved_at_format_boundary(self):
        text = BOARD.format(version=20260901, items=DRILL_ITEMS)
        for target in ('10.99', '20260901'):
            with self.subTest(target=target):
                out, report, _ = self.convert(text, target=target)
                self.assertEqual(out, text)
                self.assertFalse(report['changed'])
                self.assertFalse(report.get('warnings'))
        self.assertEqual(core.resolve_target_version('schematic', '20260901'), '20260830')
        self.assertEqual(core.resolve_target_version('worksheet', '20260901'), '20231118')

    def test_drill_chart_becomes_static_table(self):
        for target in ('10.0', '9.0', '20260831'):
            with self.subTest(target=target):
                out, report, _ = self.board(DRILL_ITEMS, version=20260901, target=target)
                root = core.parse_sexpr(out)
                table = root.child_list('table')
                self.assertIsNotNone(table)
                if target == '9.0':
                    self.assertIsNone(table.child_list('uuid'))
                else:
                    self.assertEqual(table.child_list('uuid').atom_at(1), CHART_ID)
                self.assertEqual(table.child_list('locked').atom_at(1), 'yes')
                self.assertEqual(table.child_list('layer').atom_at(1), 'Dwgs.User')
                self.assertIn('0.300 mm / 2 holes', out)
                self.assertIn(CELL_ID, out)
                self.assertIn('(drill 0.3)', out)
                self.assertEqual(len([n for n in root.children if n.head() == 'via']), 1)
                for token in ('drill_chart', 'drill_map', 'drill_symbol_profile', 'row_shapes', 'row_keys'):
                    self.assertNotIn('(' + token, out)
                for token in ('filter', 'units', 'precision', 'totals', 'column'):
                    self.assertIsNone(table.child_list(token))
                members = root.child_list('group').child_list('members')
                self.assertEqual(CHART_ID in [n.atom for n in members.children[1:]], target != '9.0')
                self.assertNotIn(MAP_ID, out)
                self.warning(report, 'static PCB table')
                self.warning(report, 'symbol marks')
                self.warning(report, 'drill map')
                self.warning(report, 'drill symbol profile')
                self.assertEqual(table.child_list('custom_property') is not None, target == '20260831')

    def test_drill_objects_removed_for_pre_table_targets(self):
        for target in ('4.0', '5.0', '6.0', '7.0', '8.0'):
            with self.subTest(target=target):
                out, report, _ = self.board(DRILL_ITEMS, version=20260901, target=target)
                root = core.parse_sexpr(out)
                for token in ('table', 'drill_chart', 'drill_map', 'drill_symbol_profile'):
                    self.assertNotIn('(' + token, out)
                for identifier in (CHART_ID, MAP_ID, CELL_ID):
                    self.assertNotIn(identifier, out)
                self.assertEqual(len([n for n in root.children if n.head() == 'via']), 1)
                self.warning(report, 'removed drill chart')
                group = root.child_list('group')
                if group:
                    self.assertEqual(len(group.child_list('members').children), 2)

    def test_table_identity_boundary(self):
        table = core.parse_sexpr(DRILL_CHART)
        table.children[0].atom = 'table'
        table.children = [n for n in table.children if n.head() not in {'filter', 'units', 'precision', 'totals', 'column', 'row_shapes', 'row_keys'}]
        for target, keep_id in [('20250906', False), ('20250907', True)]:
            out, report, _ = self.board(core.format_sexpr(table) + DRILL_GROUP, version=20260901, target=target)
            root = core.parse_sexpr(out)
            self.assertEqual(root.child_list('table').child_list('uuid') is not None, keep_id)
            members = root.child_list('group').child_list('members')
            self.assertEqual(CHART_ID in [n.atom for n in members.children[1:]], keep_id)
            self.assertIn(CELL_ID, out)
            if not keep_id:
                self.warning(report, 'PCB table UUID')
        footprint = '(footprint "Table" (version 20260901) (layer "F.Cu") ' + core.format_sexpr(table) + ')'
        out, _, _ = self.convert(footprint, '.kicad_mod', target='9.0')
        self.assertIsNone(core.parse_sexpr(out).child_list('table').child_list('uuid'))
        out, _, _ = self.board(footprint, version=20260901, target='9.0')
        self.assertIsNone(core.parse_sexpr(out).child_list('footprint').child_list('table').child_list('uuid'))
        self.assertIn(CELL_ID, out)

    def test_drill_conversion_does_not_strip_unrelated_fields(self):
        text = DRILL_ITEMS + '(property "drill_map" "keep")'
        out, _, _ = self.board(text, version=20260901)
        self.assertIn('(property "drill_map" "keep")', out)
        # Empty symbol payloads must not claim marks were lost.
        chart = core.parse_sexpr(DRILL_CHART)
        chart.children = [n for n in chart.children if n.head() != 'row_shapes']
        _, report, _ = self.board(core.format_sexpr(chart), version=20260901)
        self.assertFalse(any('symbol marks' in w for w in report.get('warnings', [])))

    def test_zero_padded_bus_connectivity_warning(self):
        for text, warn in [('DATA[00..03]', True), ('DATA[3..00]', True),
                           ('DATA[0..3]', False), ('DATA[10..13]', False)]:
            sch = '(kicad_sch (version 20260830) (generator "eeschema") (label "' + text + '" (at 0 0 0) (effects (font (size 1 1)))))'
            out, report, _ = self.convert(sch, '.kicad_sch')
            self.assertIn(text, out)
            self.assertEqual(any('zero-padded bus' in w for w in report.get('warnings', [])), warn)
        sch = '(kicad_sch (version 20260830) (generator "eeschema") (bus_alias "DATA" (members "D[00..03]")))'
        _, report, _ = self.convert(sch, '.kicad_sch', target='5.0')
        self.warning(report, 'zero-padded bus')
        _, report, _ = self.convert(sch, '.kicad_sch', target='10.99')
        self.assertFalse(any('zero-padded bus' in w for w in report.get('warnings', [])))

    def test_custom_properties_are_not_normal_fields(self):
        out, report, _ = self.board('(footprint "Test" (layer "F.Cu") (attr smd exclude_from_sim) (property "Value" "Keep") (custom_property "a" "b") (variant (name "A") (exclude_from_sim yes) (dnp yes)))')
        self.assertNotIn('custom_property', out)
        self.assertNotIn('exclude_from_sim', out)
        self.assertIn('"Keep"', out)
        self.assertIn('(dnp yes)', out)
        self.warning(report, 'custom user properties')
        self.warning(report, 'simulation exclusion')

    def test_symbol_exclude_is_retained(self):
        text = '(kicad_symbol_lib (version 20260830) (generator "kicad_symbol_editor") (symbol "Demo" (exclude_from_sim yes) (property "Value" "Keep" (custom_property "k" "v"))))'
        out, report, _ = self.convert(text, '.kicad_sym')
        self.assertIn('(exclude_from_sim yes)', out)
        self.assertNotIn('custom_property', out)
        self.warning(report, 'custom user properties')

    def test_line_endings_bake_and_shorten(self):
        out, report, _ = self.board(LINE.format(ending='(end_shape arrow (length 2) (width 1))'))
        root = core.parse_sexpr(out)
        line = root.child_list('gr_line')
        self.assertEqual(line.child_list('end').atom_at(1), '18')
        polygon = root.child_list('gr_poly')
        self.assertIsNotNone(polygon)
        self.assertEqual(polygon.child_list('layer').atom_at(1), 'F.Cu')
        self.assertEqual(polygon.child_list('fill').atom_at(1), 'solid')
        points = [core._xy_float_tuple(n) for n in core._points_xy(polygon)]
        self.assertIn((20.0, 10.0), points)
        self.assertIn((18.0, 10.5), points)
        self.assertNotEqual(polygon.child_list('uuid').atom_at(1), line.child_list('uuid').atom_at(1))
        self.assertNotIn('end_shape', out)
        self.warning(report, 'line ending')

    def test_open_arrow_uses_two_lines_not_closed_polygon(self):
        out, _, _ = self.board(LINE.format(ending='(start_shape arrow_open)'))
        root = core.parse_sexpr(out)
        lines = [n for n in root.children if n.head() == 'gr_line']
        self.assertEqual(len(lines), 3)
        self.assertIsNone(root.child_list('gr_poly'))
        self.assertEqual(lines[0].child_list('start').atom_at(1), '10')
        self.assertTrue(all(core._child_float(n.child_list('stroke'), 'width', -1) == 0.2 for n in lines))

    def test_circle_square_and_explicit_stroke(self):
        out, _, _ = self.board(LINE.format(ending='(start_shape circle (length 2)) (end_shape square (width 2) (stroke (width 0.4) (type solid)))'))
        root = core.parse_sexpr(out)
        line = root.child_list('gr_line')
        self.assertEqual(line.child_list('start').atom_at(1), '11')
        self.assertEqual(line.child_list('end').atom_at(1), '19.2')
        polys = [n for n in root.children if n.head() == 'gr_poly']
        self.assertEqual(len(polys), 2)
        self.assertEqual(len(core._points_xy(polys[0])), 33)
        self.assertEqual(core._child_float(polys[1].child_list('stroke'), 'width', -1), 0.4)

    def test_arc_and_bezier_endings(self):
        for item in ['(gr_arc (start 0 0) (mid 5 -5) (end 10 0) (stroke (width 0.2) (type solid)) (layer "F.Cu") (end_shape arrow (length 1)))', '(gr_curve (pts (xy 0 0) (xy 2 -5) (xy 8 -5) (xy 10 0)) (stroke (width 0.2) (type solid)) (layer "F.Cu") (end_shape arrow_open (length 1)))']:
            out, report, _ = self.board(item)
            self.assertNotIn('end_shape', out)
            self.warning(report, 'line ending')
            self.assertGreater(len(core.parse_sexpr(out).children), 4)

    def test_footprint_transform_bakes_new_geometry(self):
        fp = '(footprint "Demo" (version 20260831) (layer "F.Cu") (transform (translate 4 5) (rotate 90) (scale 2 3)) ' + LINE.format(ending='(end_shape arrow (length 2) (width 1))').replace('gr_line', 'fp_line') + ')'
        out, _, _ = self.convert(fp, '.kicad_mod')
        self.assertNotIn('transform', out)
        root = core.parse_sexpr(out)
        self.assertIsNotNone(root.child_list('fp_poly'))
        self.assertIn('(xy 40 30)', out)
        self.assertEqual(root.child_list('fp_line').child_list('end').atom_at(1), '36')

    def test_new_generators_keep_members_and_group_references(self):
        for kind in ['via_stitch', 'via_stack']:
            items = '(via (at 10 10) (size 0.6) (drill 0.3) (layers "F.Cu" "B.Cu") (net "N") (uuid "22222222-2222-4222-8222-222222222222")) (generated (uuid "33333333-3333-4333-8333-333333333333") (type ' + kind + ') (name "Keep group") (layer "F.Cu") (templates (template (name "via") (via (at 0 0) (size 0.6) (drill 0.3) (layers "F.Cu" "B.Cu")))) (members "22222222-2222-4222-8222-222222222222")) (group "parent" (uuid "44444444-4444-4444-8444-444444444444") (members "33333333-3333-4333-8333-333333333333"))'
            out, report, _ = self.board(items)
            root = core.parse_sexpr(out)
            self.assertIsNone(root.child_list('generated'))
            self.assertIsNotNone(root.child_list('via'))
            self.assertEqual(root.child_list('via').child_list('net').atom_at(1), 'N')
            groups = [n for n in root.children if n.head() == 'group']
            self.assertEqual(len(groups), 2)
            self.assertEqual(groups[0].atom_at(1), 'Keep group')
            self.assertEqual(groups[0].child_list('uuid').atom_at(1), '33333333-3333-4333-8333-333333333333')
            self.assertNotIn('templates', out)
            self.warning(report, kind)

    def test_generator_version_gates_do_not_remove_existing_types(self):
        items = '(generated (type tuning_pattern) (members)) (generated (type via_stitch) (members)) (generated (type via_stack) (members))'
        out, _, _ = self.board(items, target='20260818')
        self.assertIn('(type tuning_pattern)', out)
        self.assertIn('(type via_stitch)', out)
        self.assertNotIn('(type via_stack)', out)

    def test_bold_width_round_trip_and_font_exclusions(self):
        for face in ['', '(face "KiCad Font")', '(face "Arial")']:
            item = '(gr_text "T" (at 0 0) (layer "F.SilkS") (effects (font ' + face + ' (size 2 2) (thickness 0.2) (bold yes))))'
            out, report, _ = self.board(item)
            width = next(n for n in core._walk(core.parse_sexpr(out)) if n.head() == 'thickness').atom_at(1)
            self.assertEqual(width, '0.2' if 'Arial' in face else '0.32')
            upgraded, _, _ = self.convert(out, target='10.99')
            self.assertIn('(thickness 0.2)', upgraded)
        for font in ['(size 2 2) (bold yes)', '(size 2 2) (thickness 0) (bold yes)', '(size 2 2) (thickness 0.2) (bold no)']:
            out, _, _ = self.board('(gr_text "T" (at 0 0) (layer "F.SilkS") (effects (font ' + font + ')))')
            self.assertNotIn('(thickness 0.32)', out)

    def test_bold_upgrade_legacy_atom_and_old_to_old(self):
        item = '(gr_text "T" (at 0 0) (layer "F.SilkS") (effects (font (size 2 2) (thickness 0.32) bold)))'
        out, report, _ = self.board(item, version=20221018, target='10.99')
        self.assertIn('(thickness 0.2)', out)
        self.warning(report, 'bold stroke')
        out, _, _ = self.board(item, version=20241229, target='8.0')
        self.assertIn('(thickness 0.32)', out)

    def test_new_schematic_and_symbol_primitives_and_legacy_paths(self):
        shape = '(polyline (pts (xy 0 0) (xy 10 0)) (stroke (width 0.2) (type default)) (end_shape arrow (length 1)) (fill (type none)) (custom_property "k" "v"))'
        sym = '(kicad_symbol_lib (version 20260830) (generator "kicad_symbol_editor") (symbol "Demo" (property "Reference" "U" (at 0 0 0) (effects (font (size 1.27 1.27)))) (symbol "Demo_0_1" ' + shape + ')))'
        sch = '(kicad_sch (version 20260830) (generator "eeschema") (uuid "11111111-1111-4111-8111-111111111111") (paper "A4") (lib_symbols) ' + shape + ')'
        for text, extension in [(sym, '.kicad_sym'), (sch, '.kicad_sch')]:
            for target in ['10.0', '5.0']:
                out, report, _ = self.convert(text, extension, target)
                self.assertNotIn('end_shape', out)
                self.assertNotIn('custom_property', out)
                self.warning(report, 'line ending')
                self.warning(report, 'custom user properties')

    def test_drc_preserves_comments_strings_and_supported_constraints(self):
        text = '# (constraint microvia_stack_depth (max 999))\n(version 1)\n(rule "literal (microvia_stack_depth)"\n (condition "A.NetName == \\"x\\"")\n (constraint clearance (min 0.2))\n (constraint microvia_stack_depth (max 2)))\n(rule "only-new" (constraint microvia_aspect_ratio (max 0.75)))\n'
        out, report, _ = self.convert(text, '.kicad_dru')
        self.assertIn('# (constraint microvia_stack_depth (max 999))', out)
        self.assertIn('(constraint clearance (min 0.2))', out)
        self.assertIn('"literal (microvia_stack_depth)"', out)
        self.assertNotIn('(max 2)', out)
        self.assertNotIn('only-new', out)
        self.warning(report, 'microvia_stack_depth')
        self.warning(report, 'microvia_aspect_ratio')
        keep, report, _ = self.convert(text, '.kicad_dru', '10.99')
        self.assertEqual(keep, text)
        self.assertFalse(report['changed'])
        keep, _, _ = self.convert(text, '.kicad_dru', '20260830')
        self.assertEqual(keep, text)

    def test_unknown_future_source_is_not_silently_certified(self):
        _, report, _ = self.board('', version=20270101)
        self.warning(report, 'newer than the verified')


    def test_line_ending_group_members_and_exhausted_body(self):
        item = LINE.format(ending='(end_shape arrow (length 30))')
        item += '(group "g" (uuid "55555555-5555-4555-8555-555555555555") (members "11111111-1111-4111-8111-111111111111"))'
        out, _, _ = self.board(item)
        root = core.parse_sexpr(out)
        self.assertIsNone(root.child_list('gr_line'))
        self.assertEqual(root.child_list('gr_poly').child_list('uuid').atom_at(1), '11111111-1111-4111-8111-111111111111')
        out, _, _ = self.board(item.replace('(length 30)', '(length 2)'))
        root = core.parse_sexpr(out)
        members = root.child_list('group').child_list('members')
        self.assertEqual(len(members.children), 3)
        self.assertIn(root.child_list('gr_poly').child_list('uuid').atom_at(1), [n.atom for n in members.children])

    def test_pad_primitive_does_not_gain_board_item_uuid(self):
        item = '(footprint "P" (layer "F.Cu") (pad "1" smd custom (at 0 0) (size 1 1) (layers "F.Cu") (primitives ' + LINE.format(ending='(end_shape arrow)').replace('(uuid "11111111-1111-4111-8111-111111111111")', '').replace('(layer "F.Cu")', '') + ')))'
        out, _, _ = self.board(item)
        primitives = next(n for n in core._walk(core.parse_sexpr(out)) if n.head() == 'primitives')
        self.assertNotIn('(uuid', core.format_sexpr(primitives))
        self.assertIsNotNone(primitives.child_list('gr_poly'))

    def test_schematic_polygon_is_not_removed(self):
        text = '(kicad_sch (version 20260830) (polyline (pts (xy 0 0) (xy 5 0) (xy 5 5) (xy 0 0)) (stroke (width 0.2) (type default)) (fill (type background))))'
        out, _, _ = self.convert(text, '.kicad_sch')
        poly = core.parse_sexpr(out).child_list('polyline')
        self.assertEqual(len(core._points_xy(poly)), 4)
        self.assertEqual(poly.child_list('fill').child_list('type').atom_at(1), 'background')

    def test_each_new_feature_boundary(self):
        items = LINE.format(ending='(end_shape square) (custom_property "k" "v")')
        items += '(footprint "P" (layer "F.Cu") (attr smd exclude_from_sim))'
        out, _, _ = self.board(items, target='20260828')
        self.assertIn('end_shape', out)
        self.assertIn('exclude_from_sim', out)
        self.assertNotIn('custom_property', out)
        out, _, _ = self.board(items, target='20260826')
        self.assertIn('end_shape', out)
        self.assertNotIn('exclude_from_sim', out)
        out, _, _ = self.board(items, target='20260816')
        self.assertNotIn('end_shape', out)

    def test_bold_schematic_units_and_tiny_auto_threshold(self):
        text = '(kicad_symbol_lib (version 20251024) (symbol "P" (symbol "P_0_1" (text "T" (at 0 0 0) (effects (font (size 2 2) (thickness 0.0002) (bold yes)))))))'
        out, _, _ = self.convert(text, '.kicad_sym', '10.99')
        self.assertIn('(thickness 0.0002)', out)  # Upstream floors migrated bases at 2 IU.
        text = text.replace('20251024', '20260830').replace('0.0002', '0.2')
        out, report, _ = self.convert(text, '.kicad_sym')
        self.assertIn('(thickness 0.32)', out)
        self.warning(report, 'bold stroke')

    def test_invalid_ending_fails_instead_of_losing_geometry(self):
        with self.assertRaisesRegex(ValueError, 'unknown line ending'):
            self.board(LINE.format(ending='(end_shape future_unknown_shape)'))

    def test_pre_v6_groups_and_hidden_fields(self):
        items = '(setup (zone_defaults (property "F.Cu" (hatch_position 0 0))))'
        items += '(generated (type via_stack) (name "Stack") (uuid "33333333-3333-4333-8333-333333333333") (members))'
        items += '(footprint "P" (layer "F.Cu") (property "Reference" "REF" (at 0 0) (layer "F.SilkS") (hide yes) (effects (font (size 1 1)))))'
        out, report, _ = self.board(items, target='4.0')
        self.assertNotIn('(group', out)
        self.assertNotIn('zone_defaults', out)
        field = core.parse_sexpr(out).child_list('module').child_list('fp_text')
        self.assertEqual(field.children[3].head(), 'at')
        self.assertIn('hide', [n.atom for n in field.children])
        self.warning(report, 'physical members')

    def test_project_and_design_rules_conversion_together(self):
        project = self.work / 'project'
        project.mkdir()
        settings = {'board': {'design_settings': {'via_stack_presets': [{'name': 'HDI'}]}, 'ipc2581': {'mode': 'USERDEF'}}, 'schematic': {'bom_presets': [{'filter_scope': 'all'}]}, 'libraries': {'pinned_design_block_libs': ['Demo']}}
        original = json.dumps(settings)
        (project / 'demo.kicad_pro').write_text(original, encoding='utf-8')
        (project / 'demo.kicad_pcb').write_text(BOARD.format(version=20260831, items=LINE.format(ending='(end_shape circle)')), encoding='utf-8')
        rules = '(version 1)\n(rule "HDI" (constraint microvia_stack_depth (max 2)))\n'
        (project / 'demo.kicad_dru').write_text(rules, encoding='utf-8')
        output, report_path = self.work / 'project_out', self.work / 'project_report.json'
        _, _, code = core.convert(project, output, '10.0', report_path)
        self.assertEqual(code, 0)
        result = core.versioned_output_path(output, '10.0')
        self.assertEqual((result / 'demo.kicad_pro').read_text(encoding='utf-8'), original)
        self.assertNotIn('microvia_stack_depth', (result / 'demo.kicad_dru').read_text(encoding='utf-8'))
        reports = json.loads(report_path.read_text(encoding='utf-8'))['files']
        warnings = ' '.join(w for r in reports for w in r.get('warnings', []))
        self.assertIn('BOM filter_scope', warnings)
        self.assertIn('microvia stack presets', warnings)
        self.assertIn('IPC-2581', warnings)
        self.assertEqual((project / 'demo.kicad_dru').read_text(encoding='utf-8'), rules)

    @unittest.skipUnless(os.environ.get('KICAD10_CLI'), 'Set KICAD10_CLI for native schematic/symbol tests')
    def test_native_schematic_and_symbol_exports(self):
        shape = '(polyline (pts (xy 0 0) (xy 10 0)) (stroke (width 0.2) (type default)) (fill (type none)) (start_shape circle) (end_shape arrow) (custom_property "k" "v"))'
        sym = '(kicad_symbol_lib (version 20260830) (generator "kicad_symbol_editor") (symbol "Demo" (property "Reference" "U" (at 0 0 0) (effects (font (size 1.27 1.27)))) (symbol "Demo_0_1" ' + shape + ')))'
        sch = '(kicad_sch (version 20260830) (generator "eeschema") (uuid "11111111-1111-4111-8111-111111111111") (paper "A4") (lib_symbols) ' + shape + ')'
        targets = [('10.0', os.environ['KICAD10_CLI'])]
        if os.environ.get('KICAD_NATIVE_ROOT'):
            root = Path(os.environ['KICAD_NATIVE_ROOT'])
            targets.extend((v, str(root / v / 'bin/kicad-cli.exe')) for v in ('7.0', '8.0', '9.0')
                           if (root / v / 'bin/kicad-cli.exe').exists())
        for text, extension, command in [(sym, '.kicad_sym', 'sym'), (sch, '.kicad_sch', 'sch')]:
            for version, cli in targets:
                with self.subTest(kind=command, target=version):
                    _, _, path = self.convert(text, extension, version)
                    output = self.work / (command + '_' + version + '_svg')
                    result = subprocess.run([cli, command, 'export', 'svg', '-o', str(output), str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertTrue(list(output.glob('*.svg')))

    @unittest.skipUnless(os.environ.get('KICAD_SOURCE_REPO') and os.environ.get('KICAD_NATIVE_ROOT'),
                         'Set KICAD_SOURCE_REPO and KICAD_NATIVE_ROOT for upstream/native matrix')
    def test_upstream_native_board_matrix(self):
        root = Path(os.environ['KICAD_NATIVE_ROOT'])
        count = 0
        fixtures = ['via_stacks', 'line_ending_zone_flood/line_ending_zone_flood', 'line_ending_drc/line_ending_drc_fail']
        for fixture in fixtures:
            text = subprocess.check_output(['git', '-C', os.environ['KICAD_SOURCE_REPO'], 'show', '5ba95b2054:qa/data/pcbnew/' + fixture + '.kicad_pcb']).decode('utf-8')
            original_tracks = sum(n.head() in {'via', 'segment', 'arc'} for n in core.parse_sexpr(text).children)
            for version in ['4.0', '5.0', '6.0', '7.0', '8.0', '9.0', '10.0']:
                candidates = [root / version / 'bin/python.exe', root / version / 'KiCad/bin/python.exe']
                python = next((p for p in candidates if p.exists()), None)
                if python is None:
                    continue
                with self.subTest(fixture=fixture, version=version):
                    _, _, path = self.convert(text, target=version)
                    probe = ('import pcbnew,sys\n'
                             'b=pcbnew.LoadBoard(sys.argv[1])\n'
                             'assert b is not None\n'
                             't=b.GetTracks()\n'
                             'print(t.size() if hasattr(t,"size") else len(list(t)))\n')
                    result = subprocess.run([str(python), '-c', probe, str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    # Track arcs may become several segments on old targets, never disappear.
                    self.assertGreaterEqual(int(result.stdout.strip()), original_tracks)
                    count += 1
        self.assertGreater(count, 0, 'No KiCad Python installation found under KICAD_NATIVE_ROOT')

    @unittest.skipUnless(os.environ.get('KICAD1099_CLI'), 'Set KICAD1099_CLI for current nightly PCB load tests')
    def test_native_current_nightly_drill_documentation(self):
        text = BOARD.format(version=20260901, items=DRILL_ITEMS)
        source = self.work / 'nightly-drill.kicad_pcb'
        output = self.work / 'nightly-svg'
        source.write_text(text, encoding='utf-8')
        result = subprocess.run(
            [os.environ['KICAD1099_CLI'], 'pcb', 'export', 'svg', '--mode-multi',
             '--layers', 'Dwgs.User', '--output', str(output), str(source)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        svgs = list(output.glob('*.svg'))
        self.assertEqual(len(svgs), 1)
        self.assertGreater(svgs[0].stat().st_size, 0)

    @unittest.skipUnless(os.environ.get('KICAD_NATIVE_ROOT'), 'Set KICAD_NATIVE_ROOT for native drill-documentation load tests')
    def test_native_drill_documentation_matrix(self):
        root = Path(os.environ['KICAD_NATIVE_ROOT'])
        count = 0
        for version in ('4.0', '5.0', '6.0', '7.0', '8.0', '9.0', '10.0'):
            candidates = [root / version / 'bin/python.exe', root / version / 'KiCad/bin/python.exe']
            python = next((p for p in candidates if p.exists()), None)
            if python is None:
                continue
            with self.subTest(version=version):
                _, _, path = self.board(DRILL_ITEMS, version=20260901, target=version)
                probe = ('import pcbnew,sys\n'
                         'b=pcbnew.LoadBoard(sys.argv[1])\n'
                         'assert b is not None\n'
                         't=b.GetTracks()\n'
                         'assert (t.size() if hasattr(t,"size") else len(list(t))) == 1\n')
                if int(version.split('.')[0]) >= 9:
                    probe += ('tables=[d for d in b.GetDrawings() if d.GetClass()=="PCB_TABLE"]\n'
                              'assert len(tables)==1\n'
                              'pcbnew.SaveBoard(sys.argv[1]+".roundtrip", b)\n')
                result = subprocess.run([str(python), '-c', probe, str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                if int(version.split('.')[0]) >= 9:
                    saved = core.parse_sexpr(Path(str(path) + '.roundtrip').read_text(encoding='utf-8'))
                    cells = saved.child_list('table').child_list('cells')
                    self.assertEqual(cells.child_list('table_cell').atom_at(1), '0.300 mm / 2 holes')
                count += 1
        self.assertGreater(count, 0, 'No KiCad Python installation found under KICAD_NATIVE_ROOT')

    @unittest.skipUnless(os.environ.get('KICAD10_PYTHON'), 'Set KICAD10_PYTHON for native PCB load tests')
    def test_native_pcb_load(self):
        for ending in ['(end_shape arrow)', '(start_shape arrow_open)', '(end_shape circle)', '(end_shape square)']:
            _, _, path = self.board(LINE.format(ending=ending + ' (custom_property "k" "v")'))
            probe = 'import pcbnew,sys; b=pcbnew.LoadBoard(sys.argv[1]); sys.exit(0 if b else 2)'
            result = subprocess.run([os.environ['KICAD10_PYTHON'], '-c', probe, str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        text = '(gr_text "Bold" (at 10 10) (layer "F.SilkS") (effects (font (size 2 2) (thickness 0.2) (bold yes))))'
        _, _, path = self.board(text)
        probe = ('import pcbnew,sys; b=pcbnew.LoadBoard(sys.argv[1]); '
                 't=list(b.GetDrawings())[0]; print(pcbnew.ToMM(t.GetEffectiveTextPenWidth()))')
        result = subprocess.run([os.environ['KICAD10_PYTHON'], '-c', probe, str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertAlmostEqual(float(result.stdout.strip()), 0.32)


if __name__ == '__main__':
    unittest.main()
