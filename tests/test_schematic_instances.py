"""Issue #4: preserve per-instance annotation and legacy power-net semantics."""
from collections import Counter
import hashlib
import json
import os
import shutil
from pathlib import Path
import subprocess
import tempfile
import unittest
import uuid
import xml.etree.ElementTree as ET

from plugin import backport_core as core


def uid(number):
    return str(uuid.UUID(int=number))


FONT = '(effects (font (size 1.27 1.27)))'
RESISTOR = """(symbol "Regression:R"
  (pin_names (offset 0)) (in_bom yes) (on_board yes)
  (property "Reference" "R" (at 0 0 0) {font})
  (property "Value" "R" (at 0 2.54 0) {font})
  (symbol "R_0_1"
    (rectangle (start 0 -1) (end 5.08 1)
      (stroke (width 0) (type default)) (fill (type none))))
  (symbol "R_1_1"
    (pin passive line (at 0 0 0) (length 0)
      (name "1" {font}) (number "1" {font}))
    (pin passive line (at 5.08 0 180) (length 0)
      (name "2" {font}) (number "2" {font}))))""".format(font=FONT)
# A hidden generic power-input pin exposes net merging if (power) is lost.
POWER = """(symbol "Regression:Rail" (power global)
  (pin_names (offset 0)) (in_bom yes) (on_board yes)
  (property "Reference" "#PWR" (at 0 0 0) {font})
  (property "Value" "GENERIC" (at 0 2.54 0) {font})
  (symbol "Rail_1_1"
    (pin power_in line (at 0 0 90) (length 0) (hide yes)
      (name "GENERIC" {font}) (number "1" {font}))))""".format(font=FONT)


def placed_symbol(number, lib_id, value, x, references):
    paths = ' '.join('(path "{}" (reference "{}") (unit 1))'.format(path, ref)
                     for path, ref in references)
    return """(symbol (lib_id "{lib_id}") (at {x} 30 0) (unit 1)
      (in_bom yes) (on_board yes) (dnp no) (uuid "{uuid}")
      (property "Reference" "{reference}" (at {x} 28 0) {font})
      (property "Value" "{value}" (at {x} 32 0) {font})
      (property "Footprint" "" (at {x} 30 0) {font})
      (instances (project "issue4" {paths})))""".format(
        lib_id=lib_id, x=x, uuid=uid(number), reference=references[0][1],
        value=value, font=FONT, paths=paths)


def sheet(number, name, filename, pages):
    paths = ' '.join('(path "{}" (page "{}"))'.format(path, page) for path, page in pages)
    return """(sheet (at {x} 60) (size 15 15)
      (stroke (width 0) (type default)) (fill (color 0 0 0 0))
      (uuid "{uuid}")
      (property "Sheetname" "{name}" (at {x} 58 0) {font})
      (property "Sheetfile" "{filename}" (at {x} 77 0) {font})
      (instances (project "issue4" {paths})))""".format(
        x=number * 20, uuid=uid(number), name=name, filename=filename,
        font=FONT, paths=paths)


def write_project(directory):
    """A shared, nested sheet and two global rails using the same power lib_id."""
    directory.mkdir()
    root_path = '/' + uid(1)
    shared_paths = [root_path + '/' + uid(i) for i in (2, 3)]
    root_items = [
        placed_symbol(10, 'Regression:R', '10k', 20, [(root_path, 'R1')]),
        placed_symbol(11, 'Regression:R', '20k', 50, [(root_path, 'R2')]),
        placed_symbol(12, 'Regression:Rail', '+5V', 20, [(root_path, '#PWR01')]),
        placed_symbol(13, 'Regression:Rail', '+3V3', 50, [(root_path, '#PWR02')]),
        sheet(2, 'Channel A', 'shared.kicad_sch', [(root_path, '2')]),
        sheet(3, 'Channel B', 'shared.kicad_sch', [(root_path, '3')]),
    ]
    shared_items = [
        placed_symbol(20, 'Regression:R', '30k', 20, list(zip(shared_paths, ('R3', 'R4')))),
        sheet(4, 'Nested', 'leaf.kicad_sch', list(zip(shared_paths, ('4', '5')))),
    ]
    leaf_paths = [path + '/' + uid(4) for path in shared_paths]
    leaf_items = [placed_symbol(30, 'Regression:R', '40k', 20,
                                list(zip(leaf_paths, ('R5', 'R6'))))]
    for filename, number, items in (
            ('issue4', 1, root_items), ('shared', 5, shared_items), ('leaf', 6, leaf_items)):
        text = '(kicad_sch (version 20260306) (generator "eeschema") (uuid "{}") (paper "A4")\n'.format(uid(number))
        text += '(lib_symbols {} {})\n'.format(RESISTOR, POWER)
        text += '\n'.join(items)
        if filename == 'issue4':
            text += '\n(sheet_instances (path "/" (page "1")))'
        (directory / (filename + '.kicad_sch')).write_text(text + '\n)\n', encoding='utf-8')
    (directory / 'issue4.kicad_pro').write_text('{}\n', encoding='utf-8')
    return directory


def instance_blocks(path, head):
    root = core.parse_sexpr(path.read_text(encoding='utf-8'))
    return {
        node.child_list('uuid').atom_at(1): core.format_sexpr(node.child_list('instances'))
        if node.child_list('instances') else None
        for node in root.children if node.atom is None and node.head() == head
    }


def netlist_signature(path):
    root = ET.parse(path).getroot()
    components = {
        node.attrib['ref']: (node.findtext('value', ''), node.findtext('footprint', ''))
        for node in root.findall('./components/comp')
    }
    nets = {
        node.attrib['name']: frozenset((pin.attrib['ref'], pin.attrib['pin'])
                                      for pin in node.findall('node'))
        for node in root.findall('./nets/net')
    }
    return components, nets


class SchematicInstancesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='backport_issue4_')
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.source = write_project(self.work / 'source')
        self.original = {p.name: p.read_bytes() for p in self.source.iterdir()}

    def convert_project(self, target):
        destination = self.work / ('converted_' + target)
        stdout, stderr, code = core.convert(self.source, destination, target)
        self.assertEqual(code, 0, stdout + stderr)
        self.assertEqual(self.original, {p.name: p.read_bytes() for p in self.source.iterdir()})
        return core.versioned_output_path(destination, target)

    def test_modern_project_preserves_all_symbol_instances(self):
        for target in ('V7', 'V8', 'V9', 'V10'):
            output = self.convert_project(target)
            for filename in ('issue4', 'shared', 'leaf'):
                with self.subTest(target=target, schematic=filename):
                    name = filename + '.kicad_sch'
                    self.assertEqual(instance_blocks(self.source / name, 'symbol'),
                                     instance_blocks(output / name, 'symbol'))
                    root = core.parse_sexpr((output / name).read_text(encoding='utf-8'))
                    self.assertIsNone(root.child_list('symbol_instances'))

    def test_modern_nested_sheet_pages_are_not_collapsed(self):
        for target in ('V7', 'V8', 'V9', 'V10'):
            output = self.convert_project(target)
            for filename in ('issue4.kicad_sch', 'shared.kicad_sch'):
                with self.subTest(target=target, schematic=filename):
                    self.assertEqual(instance_blocks(self.source / filename, 'sheet'),
                                     instance_blocks(output / filename, 'sheet'))

    def test_legacy_hierarchy_tables_are_still_rebuilt(self):
        for target in ('V6',):
            with self.subTest(target=target):
                output = self.convert_project(target)
                root = core.parse_sexpr((output / 'issue4.kicad_sch').read_text(encoding='utf-8'))
                instances = root.child_list('symbol_instances')
                self.assertIsNotNone(instances)
                self.assertEqual(8, sum(node.head() == 'path' for node in instances.children))
                self.assertTrue(all(node.child_list('reference').atom_at(1)
                                    for node in instances.children if node.head() == 'path'))

    def test_legacy_root_identity_and_all_annotations(self):
        expected = {"R1", "R2", "R3", "R4", "R5", "R6", "#PWR01", "#PWR02"}
        for major in (6, 7):
            with self.subTest(target=major):
                output = self.convert_project('V%d' % major)
                root = core.parse_sexpr((output / 'issue4.kicad_sch').read_text(encoding='utf-8'))
                self.assertIsNotNone(root.child_list('uuid'))
                self.assertEqual(uid(1), root.child_list('uuid').atom_at(1))
                if major == 6:
                    paths = [n for n in root.child_list('symbol_instances').children if n.head() == 'path']
                    self.assertEqual(expected, {n.child_list('reference').atom_at(1) for n in paths})
                    self.assertEqual(8, len(paths))
                    for path in output.glob('*.kicad_sch'):
                        self.assertTrue(all(value is None for value in instance_blocks(path, 'symbol').values()))
                else:
                    for filename in ('issue4', 'shared', 'leaf'):
                        name = filename + '.kicad_sch'
                        self.assertEqual(instance_blocks(self.source / name, 'symbol'),
                                         instance_blocks(output / name, 'symbol'))

    def test_v6_roundtrip_restores_all_paths_and_pages(self):
        down = self.convert_project('V6')
        for major in (7, 8, 9, 10):
            with self.subTest(target=major):
                requested = self.work / ('back%d' % major)
                stdout, stderr, code = core.convert(down, requested, 'V%d' % major)
                self.assertEqual(0, code, stdout + stderr)
                output = core.versioned_output_path(requested, 'V%d' % major)
                for filename in ('issue4', 'shared', 'leaf'):
                    name = filename + '.kicad_sch'
                    for head in ('symbol', 'sheet'):
                        self.assertEqual(instance_blocks(self.source / name, head),
                                         instance_blocks(output / name, head))

    @unittest.skipUnless(os.environ.get('KICAD10_CLI') and os.environ.get('KICAD7_CLI'),
                         'Set KICAD10_CLI and KICAD7_CLI for V6/V7 netlist parity')
    def test_native_legacy_down_and_roundtrip_netlists(self):
        native_source = self.work / 'native_source'
        shutil.copytree(self.source, native_source)
        expected = self.export_netlist(os.environ['KICAD10_CLI'], native_source / 'issue4.kicad_sch',
                                       self.work / 'source.xml')
        for major in (6, 7):
            with self.subTest(target=major):
                down = self.convert_project('V%d' % major)
                native_down = self.work / ('native%d' % major)
                shutil.copytree(down, native_down)
                # V6 predates kicad-cli: explicitly use the V7 legacy reader.
                actual = self.export_netlist(os.environ['KICAD7_CLI'], native_down / 'issue4.kicad_sch',
                                             self.work / ('down%d.xml' % major))
                self.assertEqual(expected, actual)
                requested = self.work / ('back%d' % major)
                stdout, stderr, code = core.convert(down, requested, 'V10')
                self.assertEqual(0, code, stdout + stderr)
                back = core.versioned_output_path(requested, 'V10')
                actual = self.export_netlist(os.environ['KICAD10_CLI'], back / 'issue4.kicad_sch',
                                             self.work / ('back%d.xml' % major))
                self.assertEqual(expected, actual)

    def test_power_variants_preserve_shared_definition_and_are_idempotent(self):
        for major in (6, 7):
            with self.subTest(target=major):
                output = self.convert_project('V%d' % major)
                root = core.parse_sexpr((output / 'issue4.kicad_sch').read_text(encoding='utf-8'))
                definitions = {node.atom_at(1): node for node in root.child_list('lib_symbols').children
                               if node.head() == 'symbol'}
                self.assertIn('GENERIC', core.format_sexpr(definitions['Regression:Rail']))
                rail_ids = []
                for symbol in root.children:
                    if symbol.head() != 'symbol' or not symbol.child_list('lib_id'):
                        continue
                    value = core._property_value(symbol, 'Value')
                    if value not in ('+5V', '+3V3'):
                        continue
                    lib_id = symbol.child_list('lib_id').atom_at(1)
                    rail_ids.append(lib_id)
                    pin = next(node for node in core._walk(definitions[lib_id]) if node.head() == 'pin')
                    self.assertEqual(value, pin.child_list('name').atom_at(1))
                    self.assertTrue(any(node.atom == 'hide' for node in pin.children))
                self.assertEqual(2, len(set(rail_ids)))
                before = {p.name: p.read_bytes() for p in output.glob('*.kicad_sch')}
                requested = self.work / ('repeat%d' % major)
                stdout, stderr, code = core.convert(output, requested, 'V%d' % major)
                self.assertEqual(0, code, stdout + stderr)
                again = core.versioned_output_path(requested, 'V%d' % major)
                self.assertEqual(before, {p.name: p.read_bytes() for p in again.glob('*.kicad_sch')})

    def test_multiunit_references_are_not_reannotated(self):
        path = self.source / 'issue4.kicad_sch'
        root = core.parse_sexpr(path.read_text(encoding='utf-8'))
        symbols = [node for node in root.children if node.head() == 'symbol'][:2]
        for unit, symbol in enumerate(symbols, 1):
            symbol.child_list('unit').set_atom_at(1, str(unit))
            for prop in symbol.children:
                if prop.head() == 'property' and prop.atom_at(1) == 'Reference':
                    prop.set_atom_at(2, 'U1', True)
            instance = symbol.child_list('instances').child_list('project').child_list('path')
            instance.child_list('reference').set_atom_at(1, 'U1', True)
            instance.child_list('unit').set_atom_at(1, str(unit))
        # This is a structural annotation test; native multi-unit coverage uses
        # the actual KiCad 6 complex_hierarchy demo below.
        path.write_text(core.format_sexpr(root), encoding='utf-8')
        self.original[path.name] = path.read_bytes()
        down = self.convert_project('V6')
        legacy = core.parse_sexpr((down / path.name).read_text(encoding='utf-8'))
        units = [node.child_list('unit').atom_at(1)
                 for node in legacy.child_list('symbol_instances').children
                 if node.head() == 'path' and node.child_list('reference').atom_at(1) == 'U1']
        self.assertEqual(['1', '2'], units)
        requested = self.work / 'back'
        stdout, stderr, code = core.convert(down, requested, 'V10')
        self.assertEqual(0, code, stdout + stderr)
        self.assertEqual(instance_blocks(path, 'symbol'),
                         instance_blocks(core.versioned_output_path(requested, 'V10') / path.name, 'symbol'))

    def test_power_variant_collision_reuse_and_nonpower_pins(self):
        path = self.source / 'issue4.kicad_sch'
        root = core.parse_sexpr(path.read_text(encoding='utf-8'))
        libraries = root.child_list('lib_symbols')
        collision = 'Regression:Rail__backport_' + hashlib.sha256(b'+5V').hexdigest()[:12]
        reserved = core.parse_sexpr('(symbol "' + collision + '" (property "Value" "reserved"))')
        libraries.children.append(reserved)
        device = core.parse_sexpr(POWER.replace('Regression:Rail', 'Regression:HiddenDevice').replace('(power global)', ''))
        libraries.children.append(device)
        root.children.append(core.parse_sexpr(placed_symbol(90, 'Regression:Rail', '+5V', 100,
                                                           [('/' + uid(1), '#PWR03')])))
        root.children.append(core.parse_sexpr(placed_symbol(91, 'Regression:HiddenDevice', 'IC', 120,
                                                           [('/' + uid(1), 'U1')])))
        path.write_text(core.format_sexpr(root), encoding='utf-8')
        self.original[path.name] = path.read_bytes()
        output = self.convert_project('V7')
        result = core.parse_sexpr((output / path.name).read_text(encoding='utf-8'))
        rails = [node.child_list('lib_id').atom_at(1) for node in result.children
                 if node.head() == 'symbol' and core._property_value(node, 'Value') == '+5V']
        self.assertEqual([collision + '_1'] * 2, rails)
        definitions = {node.atom_at(1): node for node in result.child_list('lib_symbols').children
                       if node.head() == 'symbol'}
        self.assertEqual('reserved', core._property_value(definitions[collision], 'Value'))
        pin = next(node for node in core._walk(definitions['Regression:HiddenDevice']) if node.head() == 'pin')
        self.assertEqual('GENERIC', pin.child_list('name').atom_at(1))

    @unittest.skipUnless(os.environ.get('KICAD_NATIVE_ROOT') and os.environ.get('KICAD7_CLI')
                         and os.environ.get('KICAD10_CLI'), 'Set native root and V7/V10 CLI for genuine V6 demo')
    def test_native_genuine_v6_multiunit_hierarchy_upgrade(self):
        fixture = Path(os.environ['KICAD_NATIVE_ROOT']) / '6.0/share/kicad/demos/complex_hierarchy'
        if not fixture.is_dir():
            self.skipTest('KiCad 6 complex_hierarchy demo is not installed')
        source = self.work / 'legacy_demo'
        shutil.copytree(fixture, source)
        original = {p.relative_to(source): p.read_bytes() for p in source.rglob('*') if p.is_file()}
        native = self.work / 'native_demo'
        shutil.copytree(source, native)
        expected = self.export_netlist(os.environ['KICAD7_CLI'], native / 'complex_hierarchy.kicad_sch',
                                       self.work / 'legacy.xml')
        for major in (7, 10):
            with self.subTest(target=major):
                requested = self.work / ('legacy_to%d' % major)
                stdout, stderr, code = core.convert(source, requested, 'V%d' % major)
                self.assertEqual(0, code, stdout + stderr)
                output = core.versioned_output_path(requested, 'V%d' % major)
                actual = self.export_netlist(os.environ['KICAD%d_CLI' % major],
                                             output / 'complex_hierarchy.kicad_sch', self.work / ('real%d.xml' % major))
                self.assertEqual(expected[0], actual[0])
                # Automatic net-name selection differs between KiCad releases;
                # compare ALL connected pin sets, plus every explicit net name.
                self.assertEqual(Counter(tuple(sorted(pins)) for pins in expected[1].values()),
                                 Counter(tuple(sorted(pins)) for pins in actual[1].values()))
                for name, pins in expected[1].items():
                    if not name.startswith(('Net-(', 'unconnected-')) and '/Net-(' not in name:
                        self.assertEqual(pins, actual[1].get(name), name)
        self.assertEqual(original, {p.relative_to(source): p.read_bytes() for p in source.rglob('*') if p.is_file()})

    def test_root_page_and_matching_project_take_precedence(self):
        path = self.source / 'issue4.kicad_sch'
        root = core.parse_sexpr(path.read_text(encoding='utf-8'))
        root.child_list('sheet_instances').child_list('path').child_list('page').set_atom_at(1, '42', True)
        symbol = next(node for node in root.children if node.head() == 'symbol')
        symbol.child_list('instances').children.insert(1, core.parse_sexpr(
            '(project "other" (path "/' + uid(1) + '" (reference "R999") (unit 1)))'))
        path.write_text(core.format_sexpr(root), encoding='utf-8')
        self.original[path.name] = path.read_bytes()
        for major in (6, 7, 10):
            with self.subTest(target=major):
                output = self.convert_project('V%d' % major)
                result = core.parse_sexpr((output / path.name).read_text(encoding='utf-8'))
                self.assertEqual('42', result.child_list('sheet_instances').child_list('path').child_list('page').atom_at(1))
                if major == 6:
                    references = {node.child_list('reference').atom_at(1)
                                  for node in result.child_list('symbol_instances').children if node.head() == 'path'}
                    self.assertIn('R1', references)
                    self.assertNotIn('R999', references)
                else:
                    self.assertEqual(instance_blocks(path, 'symbol'), instance_blocks(output / path.name, 'symbol'))

    def test_modern_project_synthesizes_missing_symbol_instances(self):
        path = self.source / 'issue4.kicad_sch'
        root = core.parse_sexpr(path.read_text(encoding='utf-8'))
        symbol = next(node for node in root.children if node.head() == 'symbol')
        symbol.children = [node for node in symbol.children if node.head() != 'instances']
        path.write_text(core.format_sexpr(root), encoding='utf-8')
        self.original[path.name] = path.read_bytes()
        output = self.convert_project('V9')
        converted = core.parse_sexpr((output / path.name).read_text(encoding='utf-8'))
        symbol = next(node for node in converted.children if node.head() == 'symbol')
        instances = symbol.child_list('instances')
        self.assertIsNotNone(instances)
        project = instances.child_list('project')
        self.assertEqual('issue4', project.atom_at(1))
        self.assertEqual('/' + uid(1), project.child_list('path').atom_at(1))
        self.assertEqual('R1', project.child_list('path').child_list('reference').atom_at(1))

    def export_netlist(self, cli, schematic, destination):
        result = subprocess.run(
            [cli, 'sch', 'export', 'netlist', '--format', 'kicadxml',
             '--output', str(destination), str(schematic)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        self.assertEqual(0, result.returncode,
                         (result.stdout + result.stderr).decode('utf-8', errors='replace'))
        return netlist_signature(destination)

    @unittest.skipUnless(os.environ.get('KICAD10_CLI') and os.environ.get('KICAD9_CLI'),
                         'Set KICAD10_CLI and KICAD9_CLI for native netlist parity')
    def test_native_netlists_preserve_components_and_distinct_power_rails(self):
        # KiCad CLI may create/update project-local settings; export a copy.
        native_source = self.work / 'native_source'
        shutil.copytree(self.source, native_source)
        expected = self.export_netlist(os.environ['KICAD10_CLI'], native_source / 'issue4.kicad_sch',
                          self.work / 'source.xml')
        self.assertEqual({'R1', 'R2', 'R3', 'R4', 'R5', 'R6'}, set(expected[0]))
        self.assertIn(('R1', '1'), expected[1]['+5V'])
        self.assertIn(('R2', '1'), expected[1]['+3V3'])
        self.assertNotEqual(expected[1]['+5V'], expected[1]['+3V3'])
        for major in (8, 9, 10):
            cli = os.environ.get('KICAD%d_CLI' % major)
            if not cli:
                continue
            with self.subTest(target=major):
                output = self.convert_project('V%d' % major)
                actual = self.export_netlist(cli, output / 'issue4.kicad_sch', self.work / ('target%d.xml' % major))
                self.assertEqual(expected, actual)

    @unittest.skipUnless(os.environ.get('KICAD10_CLI') and os.environ.get('KICAD9_CLI'),
                         'Set KICAD10_CLI and KICAD9_CLI for native power-net parity')
    def test_native_single_sheet_power_rails_stay_separate(self):
        # No hierarchy rebuild: isolate the power regression from annotation loss.
        path = self.source / 'issue4.kicad_sch'
        root = core.parse_sexpr(path.read_text(encoding='utf-8'))
        root.children = [node for node in root.children if node.head() != 'sheet']
        path.write_text(core.format_sexpr(root), encoding='utf-8')
        self.original[path.name] = path.read_bytes()
        native_source = self.work / 'native_source'
        shutil.copytree(self.source, native_source)
        expected = self.export_netlist(os.environ['KICAD10_CLI'], native_source / path.name,
                                       self.work / 'source.xml')
        self.assertEqual({'R1', 'R2'}, set(expected[0]))
        self.assertEqual(frozenset({('R1', '1')}), expected[1]['+5V'])
        self.assertEqual(frozenset({('R2', '1')}), expected[1]['+3V3'])
        output = self.convert_project('V9')
        actual = self.export_netlist(os.environ['KICAD9_CLI'], output / path.name,
                                     self.work / 'target.xml')
        self.assertEqual(expected, actual)

    def test_modern_instances_preserve_other_projects_and_units(self):
        path = self.source / 'shared.kicad_sch'
        root = core.parse_sexpr(path.read_text(encoding='utf-8'))
        symbol = next(node for node in root.children if node.head() == 'symbol')
        instances = symbol.child_list('instances')
        instances.children.append(core.parse_sexpr(
            '(project "other_project" (path "/other/root" (reference "U42") (unit 2)))'))
        path.write_text(core.format_sexpr(root), encoding='utf-8')
        self.original[path.name] = path.read_bytes()
        output = self.convert_project('V9')
        self.assertEqual(instance_blocks(path, 'symbol'), instance_blocks(output / path.name, 'symbol'))


class PowerClassTests(unittest.TestCase):
    def test_power_flags_downgrade_without_losing_power_identity(self):
        with tempfile.TemporaryDirectory(prefix='backport_power_') as directory:
            work = Path(directory)
            for kind, extension in (('kicad_symbol_lib', '.kicad_sym'), ('kicad_sch', '.kicad_sch')):
                for flag in ('(power)', '(power global)', '(power local)'):
                    for target in ('V6', 'V7', 'V8', 'V9', 'V10'):
                        with self.subTest(kind=kind, flag=flag, target=target):
                            symbol = POWER.replace('(power global)', flag)
                            items = symbol if kind == 'kicad_symbol_lib' else '(lib_symbols ' + symbol + ')'
                            text = '({} (version 20260306) (generator "eeschema") {})'.format(kind, items)
                            source = work / ('source' + extension)
                            source.write_text(text, encoding='utf-8')
                            requested = work / ('output' + extension)
                            report = work / 'report.json'
                            stdout, stderr, code = core.convert(source, requested, target, report)
                            self.assertEqual(0, code, stdout + stderr)
                            output = core.versioned_output_path(requested, target)
                            root = core.parse_sexpr(output.read_text(encoding='utf-8'))
                            parent = root if kind == 'kicad_symbol_lib' else root.child_list('lib_symbols')
                            power = parent.child_list('symbol').child_list('power')
                            self.assertIsNotNone(power)
                            expected = flag if target == 'V10' else '(power)'
                            self.assertEqual(core.format_sexpr(core.parse_sexpr(expected)), core.format_sexpr(power))
                            warnings = json.loads(report.read_text(encoding='utf-8'))['files'][0].get('warnings', [])
                            promoted = any('local power' in message and 'global' in message for message in warnings)
                            self.assertEqual(flag == '(power local)' and target != 'V10', promoted)
                            self.assertEqual(text, source.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
