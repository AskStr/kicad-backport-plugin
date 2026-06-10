import json
import math
import shutil
import hashlib
from pathlib import Path
from typing import Callable, Iterable, Optional
VERSION = '0.4.1'
ESCAPES = {'n': '\n', 't': '\t', '"': '"', '\\': '\\'}

class Node:
    __slots__ = ('atom', 'quoted', 'children')

    def __init__(self, atom=None, quoted=False, children=None):
        self.atom = atom
        self.quoted = quoted
        self.children = [] if children is None else children

    @property
    def is_atom(self):
        return self.atom is not None

    def head(self):
        children = self.children
        if children:
            value = children[0].atom
            if value is not None:
                return value
        return ''

    def atom_at(self, index):
        children = self.children
        if 0 <= index < len(children):
            value = children[index].atom
            if value is not None:
                return value
        return ''

    def set_atom_at(self, index, value, quoted=False):
        children = self.children
        if 0 <= index < len(children) and children[index].atom is not None:
            children[index].atom = value
            children[index].quoted = quoted
            return True
        return False

    def child_list(self, head):
        for child in self.children:
            if child.atom is None and child.head() == head:
                return child
        return None

def atom(value, quoted=False):
    return Node(value, quoted)

def sexpr_list(*children):
    return Node(children=list(children))

def _tokenize(text):
    tokens = []
    i = 0
    if text.startswith('\ufeff'):
        i = 1
    while i < len(text):
        ch = text[i]
        if ch.isspace():
            i += 1
            continue
        if ch in '()':
            tokens.append((ch, False))
            i += 1
            continue
        if ch == '"':
            i += 1
            value = []
            while i < len(text):
                ch = text[i]
                i += 1
                if ch == '"':
                    tokens.append((''.join(value), True))
                    break
                if ch == '\\':
                    if i >= len(text):
                        raise ValueError('unterminated escape in quoted string')
                    escaped = text[i]
                    i += 1
                    value.append(ESCAPES.get(escaped, escaped))
                else:
                    value.append(ch)
            else:
                raise ValueError('unterminated quoted string')
            continue
        start = i
        while i < len(text) and text[i] not in '()' and (not text[i].isspace()):
            i += 1
        tokens.append((text[start:i], False))
    return tokens

def _parse_list(tokens, pos):
    node = sexpr_list()
    while pos < len(tokens):
        text, quoted = tokens[pos]
        pos += 1
        if text == '(' and (not quoted):
            child, pos = _parse_list(tokens, pos)
            node.children.append(child)
        elif text == ')' and (not quoted):
            return (node, pos)
        else:
            node.children.append(atom(text, quoted))
    raise ValueError("unexpected end of input: unclosed '('")

def parse_sexpr(text):
    root = None
    stack = []
    i = 1 if text.startswith('\ufeff') else 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch <= ' ' or (ch > '\x7f' and ch.isspace()):
            i += 1
            continue
        if root is not None and (not stack):
            raise ValueError('trailing tokens after root expression')
        if ch == '(':
            node = Node()
            if stack:
                stack[-1].children.append(node)
            elif root is None:
                root = node
            else:
                raise ValueError('trailing tokens after root expression')
            stack.append(node)
            i += 1
            continue
        if ch == ')':
            if not stack:
                raise ValueError("unexpected ')'")
            stack.pop()
            i += 1
            continue
        if not stack:
            raise ValueError("expected '('")
        if ch == '"':
            i += 1
            value = []
            while i < n:
                ch = text[i]
                i += 1
                if ch == '"':
                    stack[-1].children.append(Node(atom=''.join(value), quoted=True))
                    break
                if ch == '\\':
                    if i >= n:
                        raise ValueError('unterminated escape in quoted string')
                    escaped = text[i]
                    i += 1
                    value.append(ESCAPES.get(escaped, escaped))
                else:
                    value.append(ch)
            else:
                raise ValueError('unterminated quoted string')
            continue
        start = i
        while i < n:
            ch = text[i]
            if ch in '()' or ch <= ' ' or (ch > '\x7f' and ch.isspace()):
                break
            i += 1
        stack[-1].children.append(Node(atom=text[start:i]))
    if root is None:
        raise ValueError("expected '('")
    if stack:
        raise ValueError("unexpected end of input: unclosed '('")
    return root

def _needs_quotes(value):
    if not value:
        return True
    for ch in value:
        if ch in '()"' or ch <= ' ' or (ch > '\x7f' and ch.isspace()):
            return True
    return False

def _escape_atom(value):
    return value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\t', '\\t')

def _format_atom(node, cache=None):
    value = node.atom or ''
    quoted = node.quoted
    if cache is not None:
        key = (value, quoted)
        cached = cache.get(key)
        if cached is not None:
            return cached
    if node.quoted or _needs_quotes(value):
        formatted = f'"{_escape_atom(value)}"'
    else:
        formatted = value
    if cache is not None:
        cache[value, quoted] = formatted
    return formatted

def _inline_parts(node, cache):
    children = node.children
    if not children:
        return []
    parts = []
    total = 2
    for i, child in enumerate(children):
        if child.atom is None:
            return None
        value = _format_atom(child, cache)
        total += (1 if i else 0) + len(value)
        if total > 88:
            return None
        parts.append(value)
    return parts

def _write_node(node, indent, out, cache):
    if node.atom is not None:
        out.append(_format_atom(node, cache))
        return
    out.append('(')
    if not node.children:
        out.append(')')
        return
    inline_parts = _inline_parts(node, cache)
    if inline_parts is not None:
        for i, value in enumerate(inline_parts):
            if i:
                out.append(' ')
            out.append(value)
        out.append(')')
        return
    _write_node(node.children[0], indent + 2, out, cache)
    for child in node.children[1:]:
        out.append('\n')
        out.append(' ' * (indent + 2))
        _write_node(child, indent + 2, out, cache)
    out.append(')')

def format_sexpr(root):
    out = []
    _write_node(root, 0, out, {})
    out.append('\n')
    return ''.join(out)

def _write_text(path, text):
    with Path(path).open('w', encoding='utf-8', newline='') as out:
        out.write(text)

class Document:
    def __init__(self, path, root, kind, version, raw_text=''):
        self.path = path
        self.root = root
        self.kind = kind
        self.version = version
        self.raw_text = raw_text


class FileReport:
    def __init__(self, path, kind, source_version, target_version='', changed=False, warnings=None):
        self.path = path
        self.kind = kind
        self.source_version = source_version
        self.target_version = target_version
        self.changed = changed
        self.warnings = [] if warnings is None else warnings

def _is_number(value):
    return bool(value) and value.isdigit()

def _is_int_atom(value):
    if not value:
        return False
    if value[0] in '+-':
        return len(value) > 1 and value[1:].isdigit()
    return value.isdigit()

def _to_int(value, default=0):
    try:
        return int(value)
    except ValueError:
        return default

def _bool_value(value, default=True):
    lower = value.lower()
    if lower in {'yes', 'true', '1'}:
        return True
    if lower in {'no', 'false', '0'}:
        return False
    return default

def _to_float(value):
    try:
        return float(value)
    except ValueError:
        return None

def _format_float(value):
    if abs(value) < 5e-10:
        value = 0.0
    text = f'{value:.9f}'.rstrip('0').rstrip('.')
    return text or '0'

def _footprint_transform(node):
    at = node.child_list('at')
    if not at:
        return None
    x = _to_float(at.atom_at(1))
    y = _to_float(at.atom_at(2))
    angle = _to_float(at.atom_at(3)) if at.atom_at(3) else 0.0
    if x is None or y is None or angle is None:
        return None
    return (x, y, angle)

def _normalize_angle(angle):
    angle = math.fmod(angle, 360.0)
    if angle <= -180.0:
        angle += 360.0
    elif angle > 180.0:
        angle -= 360.0
    if abs(angle) < 5e-10:
        angle = 0.0
    return angle

def _point_to_footprint_local(x, y, transform):
    origin_x, origin_y, footprint_angle = transform
    radians = math.radians(-footprint_angle)
    dx = x - origin_x
    dy = y - origin_y
    return (dx * math.cos(radians) - dy * math.sin(radians), dx * math.sin(radians) + dy * math.cos(radians))

def _transform_dimension_text_to_footprint_local(text, transform):
    at = text.child_list('at')
    if not at:
        return
    x = _to_float(at.atom_at(1))
    y = _to_float(at.atom_at(2))
    world_angle = _to_float(at.atom_at(3)) if at.atom_at(3) else 0.0
    if x is None or y is None or world_angle is None:
        return
    _origin_x, _origin_y, footprint_angle = transform
    local_x, local_y = _point_to_footprint_local(x, y, transform)
    local_angle = _normalize_angle(world_angle - footprint_angle)
    at.set_atom_at(1, _format_float(local_x))
    at.set_atom_at(2, _format_float(local_y))
    if len(at.children) > 3:
        at.set_atom_at(3, _format_float(local_angle))
    elif local_angle:
        at.children.append(atom(_format_float(local_angle)))

def detect_kind(path, top_level):
    by_head = {'kicad_symbol_lib': 'symbol-library', 'kicad_sch': 'schematic', 'kicad_pcb': 'board', 'footprint': 'footprint', 'kicad_dru': 'design-rules', 'kicad_wks': 'worksheet', 'drawing_sheet': 'worksheet'}
    if top_level in by_head:
        return by_head[top_level]
    return {'.pro': 'legacy-project', '.sch': 'legacy-schematic', '.lib': 'legacy-symbol-library', '.dcm': 'legacy-symbol-documentation', '.kicad_pro': 'project', '.kicad_sym': 'symbol-library', '.kicad_sch': 'schematic', '.kicad_pcb': 'board', '.kicad_mod': 'footprint', '.kicad_dru': 'design-rules', '.kicad_wks': 'worksheet'}.get(path.suffix.lower(), 'unknown')
TARGET_VERSIONS = {'4.0': {'board': '4', 'footprint': '4'}, '5.0': {'board': '20171130', 'footprint': '20171130'}, '5.1': {'board': '20171130', 'footprint': '20171130'}, '6.0': {'symbol-library': '20211014', 'schematic': '20211123', 'board': '20211014', 'footprint': '20211014', 'worksheet': '20210606', 'design-rules': '20200610'}, '7.0': {'symbol-library': '20220914', 'schematic': '20230121', 'board': '20221018', 'footprint': '20221018', 'worksheet': '20220228', 'design-rules': '20200610'}, '8.0': {'symbol-library': '20231120', 'schematic': '20231120', 'board': '20240108', 'footprint': '20240108', 'worksheet': '20231118', 'design-rules': '20200610'}, '9.0': {'symbol-library': '20241209', 'schematic': '20250114', 'board': '20241229', 'footprint': '20241229', 'worksheet': '20231118', 'design-rules': '20200610'}, '10.0': {'symbol-library': '20251024', 'schematic': '20260306', 'board': '20260206', 'footprint': '20260206', 'worksheet': '20231118', 'design-rules': '20200610'}, '10.99': {'symbol-library': '20251024', 'schematic': '20260306', 'board': '20260603', 'footprint': '20260603', 'worksheet': '20231118', 'design-rules': '20200610'}}
DEVELOPMENT_BOARD_TARGETS = {'20260521', '20260603'}

def _normalize_alias(target):
    value = target.strip().lower()
    if value.startswith('kicad-'):
        value = value[6:]
    if value.startswith('v'):
        value = value[1:]
    if '.' not in value:
        value += '.0'
    return value

def resolve_target_version(kind, target):
    value = target.strip().lower()
    if not value:
        raise ValueError('empty target version')
    if _is_number(value):
        if value in DEVELOPMENT_BOARD_TARGETS and kind not in {'board', 'footprint'}:
            mapped = TARGET_VERSIONS['10.99'].get(kind)
            if mapped:
                return mapped
        return value
    value = _normalize_alias(value)
    if value not in TARGET_VERSIONS:
        raise ValueError(f'unsupported KiCad target version alias: {target}')
    if kind not in TARGET_VERSIONS[value]:
        raise ValueError('target version is not defined for this file type')
    return TARGET_VERSIONS[value][kind]

def target_version_suffix(target):
    value = target.strip().lower()
    if value.startswith('kicad-'):
        value = value[6:]
    if value.startswith('v'):
        value = value[1:]
    if value == '10.99':
        return 'V10_99'
    for sep in '.-_':
        if sep in value:
            value = value.split(sep, 1)[0]
    return 'V' + value.upper() if value else ''

def target_major_version(target):
    value = target.strip().lower()
    if not value:
        raise ValueError('empty target version')
    if value.startswith('kicad-'):
        value = value[6:]
    if value.startswith('v'):
        value = value[1:]
    for sep in '.-_':
        if sep in value:
            value = value.split(sep, 1)[0]
            break
    if not _is_number(value):
        raise ValueError(f'unsupported KiCad target version alias: {target}')
    return int(value)
LEGACY_KIND_FOR_SEXPR = {'schematic': 'legacy-schematic', 'symbol-library': 'legacy-symbol-library', 'project': 'legacy-project'}
SEXPR_KIND_FOR_LEGACY = {'legacy-schematic': 'schematic', 'legacy-symbol-library': 'symbol-library', 'legacy-symbol-documentation': 'symbol-library', 'legacy-project': 'project'}
EXTENSION_FOR_KIND = {'legacy-schematic': '.sch', 'legacy-symbol-library': '.lib', 'legacy-symbol-documentation': '.dcm', 'legacy-project': '.pro', 'schematic': '.kicad_sch', 'symbol-library': '.kicad_sym', 'project': '.kicad_pro', 'board': '.kicad_pcb', 'footprint': '.kicad_mod'}

def with_target_family_extension(path, target):
    source_kind = detect_kind(path, '')
    if target_major_version(target) <= 5:
        legacy_kind = LEGACY_KIND_FOR_SEXPR.get(source_kind)
        if legacy_kind:
            return path.with_suffix(EXTENSION_FOR_KIND[legacy_kind])
        return path
    sexpr_kind = SEXPR_KIND_FOR_LEGACY.get(source_kind)
    if sexpr_kind:
        return path.with_suffix(EXTENSION_FOR_KIND[sexpr_kind])
    return path

def versioned_output_path(path, target):
    output = with_target_family_extension(Path(path), target)
    label = target_version_suffix(target)
    if not label or output.stem.lower().endswith(('_' + label).lower()):
        return output
    return output.with_name(output.stem + '_' + label + output.suffix)

def load_document(path):
    text = path.read_text(encoding='utf-8-sig')
    extension_kind = detect_kind(path, '')
    if extension_kind.startswith('legacy-'):
        return load_legacy_document(path, text)
    if extension_kind == 'project':
        version = ''
        try:
            data = json.loads(text) if text.strip() else {}
            version = str(data.get('meta', {}).get('version', ''))
        except Exception:
            version = ''
        return Document(path=path, root=sexpr_list(atom('project')), kind='project', version=version, raw_text=text)
    root = parse_sexpr(text)
    kind = detect_kind(path, root.head())
    version_node = root.child_list('version')
    return Document(path=path, root=root, kind=kind, version=version_node.atom_at(1) if version_node else '', raw_text=text)

def _first_header_version(text, prefix):
    for line in text.splitlines():
        if line.startswith(prefix):
            return line[len(prefix):].strip().split()[0]
    return ''

def load_legacy_document(path, text):
    kind = detect_kind(path, '')
    if kind == 'legacy-schematic':
        major = 5 if _first_header_version(text, 'EESchema Schematic File Version ') >= '4' else 4
        version = 'legacy-sch-v4' if major >= 5 else 'legacy-sch-v2'
    elif kind == 'legacy-symbol-library':
        lib_version = _first_header_version(text, 'EESchema-LIBRARY Version ')
        version = 'legacy-lib-2.4' if lib_version >= '2.4' else 'legacy-lib-2.3'
    elif kind == 'legacy-symbol-documentation':
        version = 'legacy-dcm-2.0'
    elif kind == 'legacy-project':
        version = 'legacy-pro'
    else:
        raise ValueError('not a KiCad legacy document')
    return Document(path=path, root=sexpr_list(atom(kind)), kind=kind, version=version, raw_text=text)

def ensure_version(doc, version):
    version_node = doc.root.child_list('version')
    if version_node:
        if not version_node.set_atom_at(1, version):
            raise ValueError('document has an invalid top-level version field')
    else:
        doc.root.children.insert(1, sexpr_list(atom('version'), atom(version)))
    doc.version = version
FeatureRule = tuple
SYMBOL_RULES = ((20220126, ('text_box', 'textbox'), 'symbol text boxes are not available'), (20240529, ('embedded_files', 'embedded_file'), 'embedded files are not available'), (20241209, ('private',), 'private SCH_FIELD flags are not available'), (20250324, ('pin_group', 'pin_groups'), 'jumper pin groups are not available'), (20250829, ('rounded_rectangle', 'roundrect'), 'rounded rectangles are not available'), (20260508, ('ellipse', 'ellipse_arc'), 'native ellipse primitives are not available'))
SCHEMATIC_RULES = ((20220126, ('text_box', 'textbox'), 'schematic text boxes are not available'), (20220622, ('simulation_model', 'sim_model'), 'new simulation model format is not available'), (20240101, ('table',), 'schematic tables are not available'), (20240417, ('rule_area',), 'schematic rule areas are not available'), (20240620, ('embedded_files', 'embedded_file'), 'embedded files are not available'), (20241209, ('private',), 'private SCH_FIELD flags are not available'), (20250829, ('rounded_rectangle', 'roundrect'), 'rounded rectangles are not available'), (20250922, ('variants', 'variant'), 'schematic variants are not available'), (20260508, ('ellipse', 'ellipse_arc'), 'native ellipse primitives are not available'), (20260512, ('net_chain', 'net_chains'), 'schematic net chains are not available'))
BOARD_RULES = ((20220131, ('gr_text_box', 'fp_text_box', 'text_box', 'textbox'), 'PCB textboxes are not available'), (20220621, ('image',), 'PCB image objects are not available'), (20220818, ('net_tie', 'net_ties'), 'first-class net-tie storage is not available'), (20231007, ('generated',), 'PCB generative objects are not available'), (20240108, ('teardrop', 'teardrops', 'legacy_teardrops'), 'teardrop parameters are not available'), (20240202, ('table',), 'PCB tables are not available'), (20240609, ('tenting',), 'tenting keyword is not available'), (20240706, ('embedded_files', 'embedded_file', 'embedded_fonts'), 'embedded files are not available'), (20240928, ('component_class', 'component_classes'), 'component classes are not available'), (20240929, ('padstack',), 'complex padstacks are not available'), (20241006, ('via_stack', 'viastack'), 'via stacks are not available'), (20241009, ('rule_area',), 'placement/rule areas are not available'), (20250228, ('via_protection', 'covering', 'plugging', 'filling', 'capping'), 'IPC-4761 via protection is not available'), (20250818, ('custom_layer_count', 'custom_layer_counts'), 'custom footprint layer counts are not available'), (20250829, ('rounded_rectangle', 'roundrect'), 'rounded rectangles are not available'), (20250901, ('point',), 'PCB point objects are not available'), (20250914, ('barcode', 'pcb_barcode', 'gr_barcode', 'fp_barcode'), 'PCB barcode objects are not available'), (20251101, ('backdrill', 'tertiary_drill', 'front_post_machining', 'back_post_machining'), 'backdrill and tertiary drill fields are not available'), (20260101, ('variants', 'variant'), 'PCB variants are not available'), (20260410, ('extruded',), 'extruded footprint 3D body models are not available'), (20260508, ('gr_ellipse', 'gr_ellipse_arc', 'fp_ellipse', 'fp_ellipse_arc'), 'native PCB ellipse primitives are not available'), (20260511, ('spec_frequency', 'dielectric_model'), 'dielectric frequency-dependent stackup fields are not available'), (20260512, ('net_chains', 'net_chain'), 'PCB net chains are not available'), (20260513, ('thieving',), 'copper thieving zone fill mode is not available'))

def _walk(node):
    if node.atom is not None:
        return
    stack = [node]
    while stack:
        current = stack.pop()
        if current.atom is not None:
            continue
        yield current
        for child in reversed(current.children):
            if child.atom is None:
                stack.append(child)

def remove_descendants_by_head(root, heads):
    if root.atom is not None:
        return 0
    removed = 0
    kept = []
    for child in root.children:
        if child.atom is None and child.head() in heads:
            removed += 1
            continue
        if child.atom is None:
            removed += remove_descendants_by_head(child, heads)
        kept.append(child)
    root.children = kept
    return removed

def remove_descendants_by_rule(root, rules, target):
    active = [(rule, set(rule[1])) for rule in rules if target < rule[0]]
    if not active or root.atom is not None:
        return []
    counts = [0] * len(active)

    def visit(node):
        kept = []
        for child in node.children:
            if child.atom is None:
                child_head = child.head()
                removed = False
                for index, (_rule, heads) in enumerate(active):
                    if child_head in heads:
                        counts[index] += 1
                        removed = True
                        break
                if removed:
                    continue
                visit(child)
            kept.append(child)
        node.children = kept
    visit(root)
    return [(active[index][0], count) for index, count in enumerate(counts) if count]
DescendantRemovalRule = tuple
ContainingChildRemovalRule = tuple

def apply_descendant_removal_rules(root, warnings, rules):
    if not rules or root.atom is not None:
        return
    counts = [0] * len(rules)

    def visit(node):
        kept = []
        for child in node.children:
            if child.atom is None:
                child_head = child.head()
                removed = False
                for index, (heads, _message) in enumerate(rules):
                    if child_head in heads:
                        counts[index] += 1
                        removed = True
                        break
                if removed:
                    continue
                visit(child)
            kept.append(child)
        node.children = kept
    visit(root)
    for index, count in enumerate(counts):
        if count:
            warnings.append(rules[index][1])

def apply_structural_removal_rules(root, warnings, descendant_rules, containing_child_rules):
    if root.atom is not None:
        return
    if not descendant_rules and (not containing_child_rules):
        return
    descendant_counts = [0] * len(descendant_rules)
    containing_counts = [0] * len(containing_child_rules)

    def visit(node):
        kept = []
        for child in node.children:
            if child.atom is None:
                child_head = child.head()
                removed = False
                for index, (heads, _message) in enumerate(descendant_rules):
                    if child_head in heads:
                        descendant_counts[index] += 1
                        removed = True
                        break
                if not removed:
                    for index, (parent_head, child_head_to_find, _message) in enumerate(containing_child_rules):
                        if child_head == parent_head and child.child_list(child_head_to_find):
                            containing_counts[index] += 1
                            removed = True
                            break
                if removed:
                    continue
                visit(child)
            kept.append(child)
        node.children = kept
    visit(root)
    for index, count in enumerate(containing_counts):
        if count:
            warnings.append(containing_child_rules[index][2])
    for index, count in enumerate(descendant_counts):
        if count:
            warnings.append(descendant_rules[index][1])

def remove_children_from_parents(root, parents, children):
    removed = 0
    for node in _walk(root):
        if node.head() in parents:
            before = len(node.children)
            node.children = [c for c in node.children if c.atom is not None or c.head() not in children]
            removed += before - len(node.children)
    return removed

def remove_children_or_atoms_from_parents(root, parents, children):
    removed = 0
    for node in _walk(root):
        if node.head() not in parents:
            continue
        kept = []
        for child in node.children:
            if child.atom is not None and child.atom in children:
                removed += 1
                continue
            if child.atom is None and child.head() in children:
                removed += 1
                continue
            kept.append(child)
        node.children = kept
    return removed
ChildRemovalRule = tuple
ChildValueRewriteRule = tuple

def apply_child_removal_rules(root, warnings, rules):
    if not rules:
        return
    counts = [0] * len(rules)
    parent_heads = set()
    for parents, _children, _message in rules:
        parent_heads.update(parents)
    for node in _walk(root):
        node_head = node.head()
        if node_head not in parent_heads:
            continue
        kept = []
        for child in node.children:
            if child.atom is not None:
                kept.append(child)
                continue
            child_head = child.head()
            removed = False
            for index, (parents, children, _message) in enumerate(rules):
                if node_head in parents and child_head in children:
                    counts[index] += 1
                    removed = True
                    break
            if not removed:
                kept.append(child)
        node.children = kept
    for index, count in enumerate(counts):
        if count:
            warnings.append(rules[index][2])

def apply_child_value_rewrite_rules(root, warnings, rules):
    if not rules:
        return
    counts = [0] * len(rules)
    all_heads = set()
    for _mode, _parents, heads, _message in rules:
        all_heads.update(heads)
    for node in _walk(root):
        node_head = node.head()
        kept = []
        for child in node.children:
            if child.atom is not None:
                kept.append(child)
                continue
            child_head = child.head()
            if child_head not in all_heads:
                kept.append(child)
                continue
            handled = False
            for index, (mode, parents, heads, _message) in enumerate(rules):
                if child_head not in heads or (parents is not None and node_head not in parents):
                    continue
                if mode == 'bool-list':
                    if _bool_value(child.atom_at(1), True):
                        kept.append(atom(child_head))
                    counts[index] += 1
                    handled = True
                    break
                if mode == 'presence-bool' and len(child.children) > 1:
                    value = child.atom_at(1).lower()
                    if value in {'yes', 'true', '1'}:
                        child.children = child.children[:1]
                        kept.append(child)
                        counts[index] += 1
                        handled = True
                        break
                    if value in {'no', 'false', '0'}:
                        counts[index] += 1
                        handled = True
                        break
            if not handled:
                kept.append(child)
        node.children = kept
    for index, count in enumerate(counts):
        if count:
            warnings.append(rules[index][3])

def remove_direct_children_by_head(root, head):
    before = len(root.children)
    root.children = [c for c in root.children if c.atom is not None or c.head() != head]
    return before - len(root.children)

def rename_child_head_in_parents(root, parents, old, new):
    changed = 0
    for node in _walk(root):
        if node.head() in parents:
            for child in node.children:
                if child.atom is None and child.head() == old and child.set_atom_at(0, new):
                    changed += 1
    return changed

def remove_atoms_from_headed_lists(root, parents, atoms):
    removed = 0
    for node in _walk(root):
        if node.head() in parents:
            kept = [node.children[0]]
            for child in node.children[1:]:
                if child.atom is not None and child.atom in atoms:
                    removed += 1
                else:
                    kept.append(child)
            node.children = kept
    return removed

def unquote_atoms_in_headed_lists(root, heads, index):
    changed = 0
    for node in _walk(root):
        if node.head() in heads and 0 <= index < len(node.children):
            child = node.children[index]
            if child.atom is not None and child.quoted:
                child.quoted = False
                changed += 1
    return changed

def _legacy8_hex_id(value):
    chars = []
    for ch in value:
        if ch in '0123456789abcdefABCDEF':
            chars.append(ch.upper())
            if len(chars) == 8:
                return ''.join(chars)
    return value

def downgrade_pcb_tstamps_to_legacy5(root):
    changed = 0
    for node in _walk(root):
        if node.head() in {'tstamp', 'uuid', 'id'} and node.atom_at(1):
            mapped = _legacy8_hex_id(node.atom_at(1))
            if mapped != node.atom_at(1) and node.set_atom_at(1, mapped):
                changed += 1
    return changed

def downgrade_custom_pads_to_rects(root):
    changed = 0
    for node in _walk(root):
        if node.head() == 'pad' and node.atom_at(3) in {'custom', 'roundrect'}:
            if node.set_atom_at(3, 'rect'):
                changed += 1
            kept = []
            for child in node.children:
                if child.atom is None and child.head() in {'primitives', 'options', 'roundrect_rratio'}:
                    changed += 1
                    continue
                kept.append(child)
            node.children = kept
    return changed

def flatten_child_lists_to_atoms_in_parents(root, parents, children):
    changed = 0
    for node in _walk(root):
        if node.head() in parents:
            for i, child in enumerate(node.children):
                if child.atom is None and child.head() in children:
                    node.children[i] = atom(child.head())
                    changed += 1
    return changed

def downgrade_bool_lists_to_atoms(root, heads):
    changed = 0
    for node in _walk(root):
        kept = []
        for child in node.children:
            if child.atom is None and child.head() in heads:
                if _bool_value(child.atom_at(1), True):
                    kept.append(atom(child.head()))
                changed += 1
            else:
                kept.append(child)
        node.children = kept
    return changed

def downgrade_boolean_presence_nodes(root, heads):
    changed = 0
    for node in _walk(root):
        kept = []
        for child in node.children:
            if child.atom is None and child.head() in heads and (len(child.children) > 1):
                value = child.atom_at(1).lower()
                if value in {'yes', 'true', '1'}:
                    child.children = child.children[:1]
                    kept.append(child)
                    changed += 1
                    continue
                if value in {'no', 'false', '0'}:
                    changed += 1
                    continue
            kept.append(child)
        node.children = kept
    return changed

def downgrade_font_style_lists_to_atoms(root):
    changed = 0
    for node in _walk(root):
        if node.head() != 'font':
            continue
        kept = []
        for child in node.children:
            if child.atom is None and child.head() in {'bold', 'italic'} and (len(child.children) > 1):
                if _bool_value(child.atom_at(1), True):
                    kept.append(atom(child.head()))
                changed += 1
            else:
                kept.append(child)
        node.children = kept
    return changed

def ensure_legacy_property_ids(root):
    standard = {'Reference', 'Value', 'Footprint', 'Datasheet', 'ki_keywords', 'ki_description', 'ki_fp_filters'}
    changed = 0
    for node in _walk(root):
        if node.head() not in {'symbol', 'sheet'}:
            continue
        used_ids = set()
        for child in node.children:
            if child.atom is not None or child.head() != 'property':
                continue
            id_node = child.child_list('id')
            if id_node and _is_int_atom(id_node.atom_at(1)):
                used_ids.add(_to_int(id_node.atom_at(1)))
        next_id = max(7, max(used_ids, default=6) + 1)
        for child in node.children:
            if child.atom is not None or child.head() != 'property':
                continue
            if child.atom_at(1) in standard or child.child_list('id'):
                continue
            while next_id in used_ids:
                next_id += 1
            child.children.insert(min(3, len(child.children)), sexpr_list(atom('id'), atom(str(next_id))))
            used_ids.add(next_id)
            next_id += 1
            changed += 1
    return changed

def ensure_kicad6_standard_property_ids(root):
    standard = {
        'Reference': 0,
        'Value': 1,
        'Footprint': 2,
        'Datasheet': 3,
        'ki_keywords': 4,
        'ki_description': 5,
        'ki_fp_filters': 6,
    }
    changed = 0
    for node in _walk(root):
        if node.head() not in {'symbol', 'sheet'}:
            continue
        for child in node.children:
            if child.atom is not None or child.head() != 'property' or child.child_list('id'):
                continue
            property_id = standard.get(child.atom_at(1))
            if property_id is None:
                continue
            child.children.insert(min(3, len(child.children)), sexpr_list(atom('id'), atom(str(property_id))))
            changed += 1
    return changed

def normalize_kicad6_sheet_properties(root):
    legacy = {
        'Sheetname': ('Sheet name', '0'),
        'Sheet name': ('Sheet name', '0'),
        'Sheetfile': ('Sheet file', '1'),
        'Sheet file': ('Sheet file', '1'),
    }
    changed = 0
    for node in _walk(root):
        if node.head() != 'sheet':
            continue
        for child in node.children:
            if child.atom is not None or child.head() != 'property':
                continue
            normalized = legacy.get(child.atom_at(1))
            if not normalized:
                continue
            name, property_id = normalized
            if child.atom_at(1) != name and child.set_atom_at(1, name, True):
                changed += 1
            id_node = child.child_list('id')
            if id_node:
                if id_node.atom_at(1) != property_id and id_node.set_atom_at(1, property_id):
                    changed += 1
            else:
                child.children.insert(min(3, len(child.children)), sexpr_list(atom('id'), atom(property_id)))
                changed += 1
    return changed

def ensure_legacy_schematic_symbol_instances(root):
    if root.head() != 'kicad_sch' or not root.child_list('sheet_instances'):
        return 0
    root_uuid = _child_atom_or_empty(root, 'uuid')
    sheet_instances = sexpr_list(atom('sheet_instances'), _sheet_instance_node('/', '1'))
    symbol_instances = sexpr_list(atom('symbol_instances'))
    for child in root.children:
        if child.atom is None and child.head() == 'sheet':
            uuid = child.child_list('uuid').atom_at(1) if child.child_list('uuid') else ''
            if uuid:
                source_path = _first_project_instance_path(child)
                source_value = source_path.atom_at(1) if source_path else ''
                sheet_path = _append_legacy_instance_uuid(_normalize_legacy_sheet_path(source_value, root_uuid), uuid)
                sheet_instances.children.append(_sheet_instance_node(sheet_path, _child_atom_or_empty(source_path, 'page') or '1'))
        elif child.atom is None and child.head() == 'symbol' and child.child_list('lib_id'):
            uuid = child.child_list('uuid').atom_at(1) if child.child_list('uuid') else ''
            if uuid:
                source_path = _first_project_instance_path(child)
                source_value = source_path.atom_at(1) if source_path else uuid
                if source_value:
                    if not source_value.startswith('/'):
                        source_value = '/' + source_value
                    instance_path = _append_legacy_instance_uuid(_normalize_legacy_sheet_path(source_value, root_uuid), uuid)
                    symbol_instances.children.append(_symbol_instance_node(instance_path, child, source_path))
    if len(symbol_instances.children) <= 1:
        return 0
    kept = []
    changed = 1
    for child in root.children:
        if child.atom is None and child.head() in {'sheet_instances', 'symbol_instances'}:
            changed += 1
            continue
        kept.append(child)
    kept.append(sheet_instances)
    kept.append(symbol_instances)
    root.children = kept
    return changed

def remove_placed_symbol_pin_uuid_blocks(root):
    removed = 0
    for node in _walk(root):
        if node.head() != 'symbol':
            continue
        kept = []
        for child in node.children:
            if (
                child.atom is None
                and child.head() == 'pin'
                and len(child.children) == 3
                and child.children[1].atom is not None
                and child.children[2].atom is None
                and child.children[2].head() == 'uuid'
            ):
                removed += 1
                continue
            kept.append(child)
        node.children = kept
    return removed

def move_property_hide_to_effects(root):
    changed = 0
    for node in _walk(root):
        if node.head() != 'property':
            continue
        hidden = False
        kept = []
        for child in node.children:
            if child.atom is not None and child.atom == 'hide':
                hidden = True
                changed += 1
            elif child.atom is None and child.head() == 'hide':
                hidden = _bool_value(child.atom_at(1), True)
                changed += 1
            else:
                kept.append(child)
        node.children = kept
        effects = node.child_list('effects')
        if hidden and effects and (not effects.child_list('hide')):
            effects.children.append(atom('hide'))
            changed += 1
    return changed

def move_effects_hide_to_property(root):
    changed = 0
    for node in _walk(root):
        if node.head() != 'property' or node.child_list('hide'):
            continue
        effects = node.child_list('effects')
        if not effects:
            continue
        kept = []
        hidden = False
        for child in effects.children:
            if child.atom is not None and child.atom == 'hide':
                hidden = True
                changed += 1
            else:
                kept.append(child)
        effects.children = kept
        if hidden:
            node.children.append(sexpr_list(atom('hide'), atom('yes')))
            changed += 1
    return changed

def expand_presence_atoms_in_parents(root, parents, atoms):
    changed = 0
    for node in _walk(root):
        if node.head() not in parents:
            continue
        for i, child in enumerate(node.children):
            if child.atom is not None and child.atom in atoms:
                node.children[i] = sexpr_list(atom(child.atom), atom('yes'))
                changed += 1
    return changed

def expand_font_style_atoms(root):
    return expand_presence_atoms_in_parents(root, {'font'}, {'bold', 'italic'})

def normalize_bool_values(root, heads):
    changed = 0
    for node in _walk(root):
        if node.head() in heads and len(node.children) > 1:
            value = node.atom_at(1).lower()
            if value in {'true', '1'} and node.set_atom_at(1, 'yes'):
                changed += 1
            elif value in {'false', '0'} and node.set_atom_at(1, 'no'):
                changed += 1
    return changed

def remove_id_from_standard_properties(root):
    changed = 0
    for node in _walk(root):
        if node.head() != 'property':
            continue
        kept = []
        for child in node.children:
            if child.atom is None and child.head() == 'id':
                changed += 1
            else:
                kept.append(child)
        node.children = kept
    return changed

def upgrade_text_box_start_end(root):
    changed = 0
    for node in _walk(root):
        if node.head() not in {'text_box', 'textbox'}:
            continue
        start = node.child_list('start')
        end = node.child_list('end')
        if not start or not end or node.child_list('at') or node.child_list('size'):
            continue
        x1 = _to_float(start.atom_at(1))
        y1 = _to_float(start.atom_at(2))
        x2 = _to_float(end.atom_at(1))
        y2 = _to_float(end.atom_at(2))
        if x1 is None or y1 is None or x2 is None or (y2 is None):
            continue
        start.set_atom_at(0, 'at')
        end.set_atom_at(0, 'size')
        end.set_atom_at(1, _format_float(x2 - x1))
        end.set_atom_at(2, _format_float(y2 - y1))
        changed += 1
    return changed

def upgrade_pcb_page_to_paper(root):
    if root.head() != 'kicad_pcb':
        return 0
    changed = 0
    for child in root.children:
        if child.atom is None and child.head() == 'page':
            if child.set_atom_at(0, 'paper'):
                changed += 1
            if child.atom_at(1) and child.set_atom_at(1, child.atom_at(1), True):
                changed += 1
    return changed

def _xy_list_node(head, x, y):
    return sexpr_list(atom(head), atom(_format_float(x)), atom(_format_float(y)))

def upgrade_legacy_arc_angles(root):
    changed = 0
    for node in _walk(root):
        if node.head() not in {'fp_arc', 'gr_arc'}:
            continue
        center = node.child_list('start')
        start = node.child_list('end')
        angle = node.child_list('angle')
        if not center or not start or not angle or not angle.atom_at(1):
            continue
        cx = _to_float(center.atom_at(1))
        cy = _to_float(center.atom_at(2))
        sx = _to_float(start.atom_at(1))
        sy = _to_float(start.atom_at(2))
        degrees = _to_float(angle.atom_at(1))
        if cx is None or cy is None or sx is None or sy is None or degrees is None:
            continue
        radians = math.radians(degrees)
        vx = sx - cx
        vy = sy - cy

        def rotate_point(value):
            return (
                cx + vx * math.cos(value) - vy * math.sin(value),
                cy + vx * math.sin(value) + vy * math.cos(value),
            )

        mid_x, mid_y = rotate_point(radians / 2.0)
        end_x, end_y = rotate_point(radians)
        center.set_atom_at(1, _format_float(sx))
        center.set_atom_at(2, _format_float(sy))
        start.set_atom_at(1, _format_float(end_x))
        start.set_atom_at(2, _format_float(end_y))
        kept = []
        inserted_mid = False
        for child in node.children:
            if child is angle:
                continue
            kept.append(child)
            if child is center and not inserted_mid:
                kept.append(_xy_list_node('mid', mid_x, mid_y))
                inserted_mid = True
        node.children = kept
        changed += 1
    return changed

def remove_legacy_graphic_line_angles(root):
    changed = 0
    for node in _walk(root):
        if node.head() not in {'fp_line', 'gr_line'}:
            continue
        kept = []
        for child in node.children:
            if child.atom is None and child.head() == 'angle':
                changed += 1
                continue
            kept.append(child)
        node.children = kept
    return changed

def upgrade_board_net_codes_to_names(root):
    if root.head() != 'kicad_pcb':
        return 0
    code_to_name = {}
    for child in root.children:
        if child.atom is None and child.head() == 'net' and child.atom_at(1) and child.atom_at(2):
            code_to_name[child.atom_at(1)] = child.atom_at(2)
    if not code_to_name:
        return 0
    changed = 0

    def rewrite(node, parent=''):
        nonlocal changed
        if node.head() == 'net' and node.atom_at(1) in code_to_name and (parent != 'kicad_pcb'):
            node.set_atom_at(1, code_to_name[node.atom_at(1)], True)
            if len(node.children) > 2:
                node.children = node.children[:2]
            changed += 1
        head = node.head()
        for child in node.children:
            if child.atom is None:
                rewrite(child, head)
    rewrite(root)
    return changed

def ensure_zone_filled_polygon_layers(root):
    changed = 0
    for zone in _walk(root):
        if zone.head() != 'zone':
            continue
        zone_layer = zone.child_list('layer')
        layer_name = zone_layer.atom_at(1) if zone_layer else ''
        if not layer_name:
            continue
        for polygon in zone.children:
            if polygon.atom is None and polygon.head() == 'filled_polygon' and (not polygon.child_list('layer')):
                polygon.children.insert(1, sexpr_list(atom('layer'), atom(layer_name, True)))
                changed += 1
    return changed

def downgrade_tenting_to_legacy_atoms(root):
    changed = 0
    for node in _walk(root):
        if node.head() != 'tenting':
            continue
        front_node = node.child_list('front')
        back_node = node.child_list('back')
        if not front_node and (not back_node):
            continue
        children = [atom('tenting')]
        if front_node and _bool_value(front_node.atom_at(1), True):
            children.append(atom('front'))
        if back_node and _bool_value(back_node.atom_at(1), True):
            children.append(atom('back'))
        if len(children) == 1:
            children.append(atom('none'))
        node.children = children
        changed += 1
    return changed

def _property_node(name, value):
    return sexpr_list(atom('property'), atom(name, True), atom(value, True))

def downgrade_pcb_footprint_fields(root):
    changed = 0
    for node in _walk(root):
        if node.head() not in {'footprint', 'module'}:
            continue
        kept = []
        for child in node.children:
            if child.atom is not None:
                kept.append(child)
                continue
            if child.head() == 'property':
                name = child.atom_at(1)
                if name in {'Reference', 'Value'}:
                    kind = 'reference' if name == 'Reference' else 'value'
                    text = sexpr_list(atom('fp_text'), atom(kind), atom(child.atom_at(2), True))
                    if _property_hidden(child):
                        text.children.append(atom('hide'))
                    for sub in child.children[3:]:
                        if sub.atom is None and sub.head() == 'hide':
                            continue
                        elif sub.atom is None and sub.head() == 'effects':
                            sub.children = [
                                item for item in sub.children
                                if not (item.atom == 'hide' or (item.atom is None and item.head() == 'hide'))
                            ]
                            text.children.append(sub)
                        else:
                            text.children.append(sub)
                    kept.append(text)
                    changed += 1
                    continue
                if name == 'Description' and child.set_atom_at(1, 'ki_description', True):
                    changed += 1
                if len(child.children) > 3:
                    child.children = child.children[:3]
                    changed += 1
            elif child.head() == 'sheetname':
                if child.atom_at(1):
                    kept.append(_property_node('Sheetname', child.atom_at(1)))
                    changed += 1
                continue
            elif child.head() == 'sheetfile':
                if child.atom_at(1):
                    kept.append(_property_node('Sheetfile', child.atom_at(1)))
                    changed += 1
                continue
            kept.append(child)
        node.children = kept
    return changed

def downgrade_user_layer_types(root):
    changed = 0
    for node in _walk(root):
        if node.head() == 'layers':
            for layer in node.children:
                if layer.atom is None and len(layer.children) >= 4:
                    if layer.atom_at(1).startswith('User.') and layer.atom_at(2) in {'front', 'back', 'auxiliary'}:
                        layer.set_atom_at(2, 'user')
                        changed += 1
    return changed

def downgrade_pcbplotparams_bools(root):
    changed = 0
    for node in _walk(root):
        if node.head() == 'pcbplotparams':
            for child in node.children:
                if child.atom is None and len(child.children) > 1:
                    value = child.atom_at(1).lower()
                    if value == 'yes' and child.set_atom_at(1, 'true'):
                        changed += 1
                    elif value == 'no' and child.set_atom_at(1, 'false'):
                        changed += 1
    return changed

def _legacy5_layer_name(name):
    if name == 'User.Drawings':
        return 'Dwgs.User'
    if name == 'User.Comments':
        return 'Cmts.User'
    if name in {'User.Eco1', 'User.3'}:
        return 'Eco1.User'
    if name in {'User.Eco2', 'User.4'}:
        return 'Eco2.User'
    if name == 'User.2':
        return 'Cmts.User'
    if name.startswith('User.'):
        return 'Dwgs.User'
    return name

def downgrade_pcb_header_to_legacy5(root):
    if not root or root.head() != 'kicad_pcb':
        return 0
    changed = 0
    has_host = False
    for child in root.children:
        if child.atom is not None:
            continue
        if child.head() in {'generator', 'host'}:
            if child.head() == 'generator' and child.set_atom_at(0, 'host'):
                changed += 1
            has_host = True
            if len(child.children) < 2:
                child.children.append(atom('pcbnew'))
                changed += 1
            elif child.set_atom_at(1, 'pcbnew'):
                changed += 1
            if len(child.children) < 3:
                child.children.append(atom('5.0.2'))
                changed += 1
            elif child.set_atom_at(2, '5.0.2'):
                changed += 1
            if len(child.children) > 3:
                child.children = child.children[:3]
                changed += 1
        elif child.head() == 'paper':
            if child.set_atom_at(0, 'page'):
                changed += 1
            if len(child.children) > 1 and child.children[1].atom is not None:
                child.children[1].quoted = False
        elif child.head() == 'layers':
            kept = [child.children[0]] if child.children else []
            seen = set()
            for layer in child.children[1:]:
                if layer.atom is not None or not layer.head():
                    continue
                layer_name = layer.atom_at(1)
                mapped = _legacy5_layer_name(layer_name)
                if layer_name.startswith('User.') and mapped == 'Dwgs.User' and layer_name not in {'User.Drawings', 'User.Comments', 'User.Eco1', 'User.Eco2', 'User.2', 'User.3', 'User.4'}:
                    changed += 1
                    continue
                if mapped != layer_name and layer.set_atom_at(1, mapped):
                    changed += 1
                if len(layer.children) > 3:
                    layer.children = layer.children[:3]
                    changed += 1
                final_name = layer.atom_at(1)
                if final_name not in seen:
                    seen.add(final_name)
                    kept.append(layer)
                else:
                    changed += 1
            if len(kept) != len(child.children):
                child.children = kept
    if not has_host:
        insert_at = 1
        for index, child in enumerate(root.children):
            if child.atom is None and child.head() == 'version':
                insert_at = index + 1
                break
        root.children.insert(insert_at, sexpr_list(atom('host'), atom('pcbnew'), atom('5.0.2')))
        changed += 1
    return changed

def downgrade_layer_refs_to_legacy5(root):
    changed = 0
    for node in _walk(root):
        if node.head() == 'layer' and node.atom_at(1):
            mapped = _legacy5_layer_name(node.atom_at(1))
            if mapped != node.atom_at(1) and node.set_atom_at(1, mapped):
                changed += 1
        elif node.head() == 'layers':
            for index in range(1, len(node.children)):
                child = node.children[index]
                if child.atom is None:
                    continue
                mapped = _legacy5_layer_name(child.atom)
                if mapped != child.atom:
                    child.atom = mapped
                    changed += 1
    return changed

def downgrade_pcb_user_layers_to_fixed(root):
    if not root or root.head() != 'kicad_pcb':
        return 0
    changed = 0
    for node in _walk(root):
        if node.head() == 'layers':
            kept = [node.children[0]] if node.children else []
            seen = set()
            for layer in node.children[1:]:
                if layer.atom is not None or not layer.head():
                    continue
                layer_name = layer.atom_at(1)
                mapped = _legacy5_layer_name(layer_name)
                if layer_name.startswith('User.') and mapped == 'Dwgs.User' and layer_name not in {'User.Drawings', 'User.Comments', 'User.Eco1', 'User.Eco2', 'User.2', 'User.3', 'User.4'}:
                    changed += 1
                    continue
                if mapped != layer_name and layer.set_atom_at(1, mapped):
                    changed += 1
                if len(layer.children) > 3:
                    layer.children = layer.children[:3]
                    changed += 1
                final_name = layer.atom_at(1)
                if final_name not in seen:
                    seen.add(final_name)
                    kept.append(layer)
                else:
                    changed += 1
            if len(kept) != len(node.children):
                node.children = kept
        elif node.head() == 'layer' and node.atom_at(1):
            mapped = _legacy5_layer_name(node.atom_at(1))
            if mapped != node.atom_at(1) and node.set_atom_at(1, mapped):
                changed += 1
    return changed

def rename_footprints_to_modules_legacy5(root):
    changed = 0
    for node in _walk(root):
        if node.head() == 'footprint' and node.set_atom_at(0, 'module'):
            changed += 1
    return changed

def downgrade_model_offsets_to_legacy_at(root):
    changed = 0
    for node in _walk(root):
        if node.head() != 'model':
            continue
        for child in node.children:
            if child.atom is not None or child.head() != 'offset':
                continue
            if child.set_atom_at(0, 'at'):
                changed += 1
            xyz = child.child_list('xyz')
            if not xyz:
                continue
            for index in range(1, min(4, len(xyz.children))):
                value = _to_float(xyz.atom_at(index))
                if value is None:
                    continue
                if xyz.set_atom_at(index, _format_float(value / 25.4)):
                    changed += 1
    return changed

def downgrade_pcb_stroke_to_legacy_width(root):
    graphic_parents = {
        'gr_line', 'gr_arc', 'gr_circle', 'gr_rect', 'gr_poly', 'gr_curve',
        'fp_line', 'fp_arc', 'fp_circle', 'fp_rect', 'fp_poly', 'fp_curve',
    }
    changed = 0
    for node in _walk(root):
        if node.head() not in graphic_parents:
            continue
        kept = []
        for child in node.children:
            if child.atom is None and child.head() == 'stroke':
                width = child.child_list('width')
                if width and width.atom_at(1):
                    kept.append(sexpr_list(atom('width'), atom(width.atom_at(1))))
                changed += 1
                continue
            kept.append(child)
        node.children = kept
    return changed

def _legacy_arc_from_midpoint(start, mid, end):
    sx = _to_float(start.atom_at(1)) if start else None
    sy = _to_float(start.atom_at(2)) if start else None
    mx = _to_float(mid.atom_at(1)) if mid else None
    my = _to_float(mid.atom_at(2)) if mid else None
    ex = _to_float(end.atom_at(1)) if end else None
    ey = _to_float(end.atom_at(2)) if end else None
    if None in {sx, sy, mx, my, ex, ey}:
        return None
    d = 2.0 * (sx * (my - ey) + mx * (ey - sy) + ex * (sy - my))
    if abs(d) < 1e-9:
        return None
    s2 = sx * sx + sy * sy
    m2 = mx * mx + my * my
    e2 = ex * ex + ey * ey
    center_x = (s2 * (my - ey) + m2 * (ey - sy) + e2 * (sy - my)) / d
    center_y = (s2 * (ex - mx) + m2 * (sx - ex) + e2 * (mx - sx)) / d

    def normalize(radians):
        value = math.fmod(radians, 2.0 * math.pi)
        if value < 0.0:
            value += 2.0 * math.pi
        return value

    start_angle = math.atan2(sy - center_y, sx - center_x)
    mid_angle = math.atan2(my - center_y, mx - center_x)
    end_angle = math.atan2(ey - center_y, ex - center_x)
    ccw_sweep = normalize(end_angle - start_angle)
    ccw_mid = normalize(mid_angle - start_angle)
    sweep = ccw_sweep if ccw_mid <= ccw_sweep + 1e-9 else ccw_sweep - 2.0 * math.pi
    return (center_x, center_y, sweep * 180.0 / math.pi)

def downgrade_pcb_arcs_to_legacy_angles(root):
    changed = 0
    for node in _walk(root):
        if node.head() not in {'fp_arc', 'gr_arc'}:
            continue
        start = node.child_list('start')
        mid = node.child_list('mid')
        end = node.child_list('end')
        converted = _legacy_arc_from_midpoint(start, mid, end)
        if not converted:
            continue
        center_x, center_y, angle = converted
        start.set_atom_at(1, _format_float(center_x))
        start.set_atom_at(2, _format_float(center_y))
        kept = []
        for child in node.children:
            if child is mid:
                changed += 1
                continue
            kept.append(child)
            if child is end:
                kept.append(sexpr_list(atom('angle'), atom(_format_float(angle))))
        node.children = kept
        changed += 1
    return changed

def _legacy_pcb_line_from_rect(head, x1, y1, x2, y2, rect):
    line = sexpr_list(
        atom(head),
        sexpr_list(atom('start'), atom(_format_float(x1)), atom(_format_float(y1))),
        sexpr_list(atom('end'), atom(_format_float(x2)), atom(_format_float(y2))),
    )
    width = rect.child_list('width')
    if width:
        line.children.append(_clone_node(width))
    layer = rect.child_list('layer')
    if layer:
        line.children.append(_clone_node(layer))
    tstamp = rect.child_list('tstamp') or rect.child_list('uuid')
    if tstamp:
        line.children.append(_clone_node(tstamp))
    return line

def _legacy_lines_from_pcb_rect(rect):
    start = rect.child_list('start')
    end = rect.child_list('end')
    if not start or not end:
        return []
    x1 = _to_float(start.atom_at(1))
    y1 = _to_float(start.atom_at(2))
    x2 = _to_float(end.atom_at(1))
    y2 = _to_float(end.atom_at(2))
    if x1 is None or y1 is None or x2 is None or y2 is None:
        return []
    head = 'fp_line' if rect.head() == 'fp_rect' else 'gr_line'
    return [
        _legacy_pcb_line_from_rect(head, x1, y1, x2, y1, rect),
        _legacy_pcb_line_from_rect(head, x2, y1, x2, y2, rect),
        _legacy_pcb_line_from_rect(head, x2, y2, x1, y2, rect),
        _legacy_pcb_line_from_rect(head, x1, y2, x1, y1, rect),
    ]

def _rect_pts_node(x1, y1, x2, y2):
    return sexpr_list(
        atom('pts'),
        sexpr_list(atom('xy'), atom(_format_float(x1)), atom(_format_float(y1))),
        sexpr_list(atom('xy'), atom(_format_float(x2)), atom(_format_float(y1))),
        sexpr_list(atom('xy'), atom(_format_float(x2)), atom(_format_float(y2))),
        sexpr_list(atom('xy'), atom(_format_float(x1)), atom(_format_float(y2))),
    )

def _pcb_rect_fill_is_solid(rect):
    fill = rect.child_list('fill') if rect else None
    return bool(fill and fill.atom_at(1).lower() in {'yes', 'solid'})

def _is_copper_layer_name(layer):
    return layer in {'F.Cu', 'B.Cu'} or layer.endswith('.Cu')

def _legacy_pcb_poly_from_rect(rect, x1, y1, x2, y2):
    poly = sexpr_list(atom('fp_poly' if rect.head() == 'fp_rect' else 'gr_poly'), _rect_pts_node(x1, y1, x2, y2))
    width = rect.child_list('width')
    if width:
        poly.children.append(_clone_node(width))
    layer = rect.child_list('layer')
    if layer:
        poly.children.append(_clone_node(layer))
    tstamp = rect.child_list('tstamp') or rect.child_list('uuid')
    if tstamp:
        poly.children.append(_clone_node(tstamp))
    return poly

def _legacy_pcb_zone_from_rect(rect, x1, y1, x2, y2):
    if rect.head() != 'gr_rect':
        return None
    net = rect.child_list('net')
    layer = rect.child_list('layer')
    if not net or not layer or not _is_copper_layer_name(layer.atom_at(1)):
        return None
    width = '0.0254'
    rect_width = rect.child_list('width')
    if rect_width and (_to_float(rect_width.atom_at(1)) or 0.0) > 0.0:
        width = rect_width.atom_at(1)
    zone = sexpr_list(
        atom('zone'),
        _clone_node(net),
        _clone_node(layer),
        sexpr_list(atom('hatch'), atom('none'), atom('0.1')),
        sexpr_list(atom('connect_pads'), atom('yes'), sexpr_list(atom('clearance'), atom('0'))),
        sexpr_list(atom('min_thickness'), atom(width)),
        sexpr_list(atom('fill'), atom('yes')),
        sexpr_list(atom('polygon'), _rect_pts_node(x1, y1, x2, y2)),
        sexpr_list(atom('filled_polygon'), _clone_node(layer), _rect_pts_node(x1, y1, x2, y2)),
    )
    tstamp = rect.child_list('tstamp') or rect.child_list('uuid')
    if tstamp:
        zone.children.append(_clone_node(tstamp))
    return zone

def _legacy_shapes_from_pcb_rect(rect):
    start = rect.child_list('start')
    end = rect.child_list('end')
    if not start or not end:
        return []
    x1 = _to_float(start.atom_at(1))
    y1 = _to_float(start.atom_at(2))
    x2 = _to_float(end.atom_at(1))
    y2 = _to_float(end.atom_at(2))
    if x1 is None or y1 is None or x2 is None or y2 is None:
        return []
    if _pcb_rect_fill_is_solid(rect):
        zone = _legacy_pcb_zone_from_rect(rect, x1, y1, x2, y2)
        if zone:
            return [zone]
        return [_legacy_pcb_poly_from_rect(rect, x1, y1, x2, y2)]
    return _legacy_lines_from_pcb_rect(rect)

def downgrade_pcb_rects_to_legacy_lines(root):
    changed = 0

    def visit(node):
        nonlocal_changed = 0
        kept = []
        for child in node.children:
            if child.atom is None and child.head() in {'gr_rect', 'fp_rect'}:
                shapes = _legacy_shapes_from_pcb_rect(child)
                if shapes:
                    kept.extend(shapes)
                    nonlocal_changed += 1
                    continue
            if child.atom is None:
                nonlocal_changed += visit(child)
            kept.append(child)
        node.children = kept
        return nonlocal_changed

    changed += visit(root)
    return changed

def _legacy_track_segment_node(x1, y1, x2, y2, arc_node):
    segment = sexpr_list(
        atom('segment'),
        sexpr_list(atom('start'), atom(_format_float(x1)), atom(_format_float(y1))),
        sexpr_list(atom('end'), atom(_format_float(x2)), atom(_format_float(y2))),
    )
    width = arc_node.child_list('width')
    if width:
        segment.children.append(_clone_node(width))
    layer = arc_node.child_list('layer')
    if layer:
        segment.children.append(_clone_node(layer))
    net = arc_node.child_list('net')
    if net:
        segment.children.append(_clone_node(net))
    return segment

def _legacy_segments_from_track_arc(arc_node):
    start = arc_node.child_list('start')
    mid = arc_node.child_list('mid')
    end = arc_node.child_list('end')
    converted = _legacy_arc_from_midpoint(start, mid, end)
    if not converted or not start or not end:
        return []
    center_x, center_y, angle_degrees = converted
    sx = _to_float(start.atom_at(1))
    sy = _to_float(start.atom_at(2))
    ex = _to_float(end.atom_at(1))
    ey = _to_float(end.atom_at(2))
    if sx is None or sy is None or ex is None or ey is None:
        return []
    radius = math.hypot(sx - center_x, sy - center_y)
    start_angle = math.atan2(sy - center_y, sx - center_x)
    sweep = math.radians(angle_degrees)
    count = max(1, int(math.ceil(abs(angle_degrees) / 10.0)))
    segments = []
    prev_x = sx
    prev_y = sy
    for index in range(1, count + 1):
        t = float(index) / float(count)
        angle = start_angle + sweep * t
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        if index == count:
            x = ex
            y = ey
        segments.append(_legacy_track_segment_node(prev_x, prev_y, x, y, arc_node))
        prev_x = x
        prev_y = y
    return segments

def downgrade_pcb_track_arcs_to_segments(root):
    changed = 0

    def visit(node):
        nonlocal_changed = 0
        kept = []
        for child in node.children:
            if child.atom is None and child.head() == 'arc':
                segments = _legacy_segments_from_track_arc(child)
                if segments:
                    kept.extend(segments)
                    nonlocal_changed += 1
                    continue
            if child.atom is None:
                nonlocal_changed += visit(child)
            kept.append(child)
        node.children = kept
        return nonlocal_changed

    changed += visit(root)
    return changed

def _legacy_layer_selector_node(layer):
    return sexpr_list(atom('layer'), atom(layer))

def _zone_layer_names(zone):
    layer = zone.child_list('layer')
    if layer and layer.atom_at(1):
        return [layer.atom_at(1)]
    layer_list = zone.child_list('layers')
    if not layer_list:
        return []
    names = []
    seen = set()
    for child in layer_list.children[1:]:
        if child.atom is None or not child.atom or child.atom in seen:
            continue
        seen.add(child.atom)
        names.append(child.atom)
    return names

def _filled_polygon_layer_name(filled_polygon):
    layer = filled_polygon.child_list('layer')
    return layer.atom_at(1) if layer else ''

def _zone_has_layered_filled_polygons(zone):
    for child in zone.children:
        if child.atom is None and child.head() == 'filled_polygon' and _filled_polygon_layer_name(child):
            return True
    return False

def _legacy_zone_for_single_layer(zone_node, layer_name, filter_layered_fills):
    zone = _clone_node(zone_node)
    kept = []
    inserted_layer = False
    for child in zone.children:
        if child.atom is None and child.head() in {'layer', 'layers'}:
            if not inserted_layer:
                kept.append(_legacy_layer_selector_node(layer_name))
                inserted_layer = True
            continue
        if filter_layered_fills and child.atom is None and child.head() == 'filled_polygon':
            fill_layer = _filled_polygon_layer_name(child)
            if fill_layer and fill_layer != layer_name:
                continue
        kept.append(child)
    if not inserted_layer:
        insert_at = 1 if len(kept) > 1 else len(kept)
        kept.insert(insert_at, _legacy_layer_selector_node(layer_name))
    zone.children = kept
    return zone

def split_multilayer_zones_to_legacy_single_layer_zones(root):
    changed = 0

    def visit(node):
        nonlocal_changed = 0
        kept = []
        for child in node.children:
            if child.atom is None and child.head() == 'zone' and child.child_list('layers'):
                layer_names = _zone_layer_names(child)
                if layer_names:
                    layered_fills = _zone_has_layered_filled_polygons(child)
                    for layer_name in layer_names:
                        kept.append(_legacy_zone_for_single_layer(child, layer_name, layered_fills))
                    nonlocal_changed += len(layer_names)
                    continue
            if child.atom is None:
                nonlocal_changed += visit(child)
            kept.append(child)
        node.children = kept
        return nonlocal_changed

    changed += visit(root)
    return changed

def downgrade_shape_fill_no_to_none(root):
    heads = {'gr_rect', 'gr_circle', 'gr_poly', 'fp_rect', 'fp_circle', 'fp_poly'}
    changed = 0
    for node in _walk(root):
        if node.head() in heads:
            fill = node.child_list('fill')
            if fill and fill.atom_at(1).lower() == 'no' and fill.set_atom_at(1, 'none'):
                changed += 1
    return changed

def downgrade_shape_hatch_fills(root):
    heads = {'gr_rect', 'gr_circle', 'gr_poly', 'fp_rect', 'fp_circle', 'fp_poly'}
    changed = 0
    for node in _walk(root):
        if node.head() in heads:
            fill = node.child_list('fill')
            if fill and fill.atom_at(1) in {'hatch', 'reverse_hatch', 'cross_hatch'}:
                fill.set_atom_at(1, 'yes')
                changed += 1
    return changed

def ensure_zone_filled_areas_thickness(root):
    changed = 0
    for node in _walk(root):
        if node.head() == 'zone' and node.child_list('filled_polygon') and (not node.child_list('filled_areas_thickness')):
            insert_at = len(node.children)
            for i, child in enumerate(node.children[1:], 1):
                if child.atom is None and child.head() == 'fill':
                    insert_at = i
                    break
            node.children.insert(insert_at, sexpr_list(atom('filled_areas_thickness'), atom('no')))
            changed += 1
    return changed

def remove_nodes_containing_child(root, parent_head, child_head):
    removed = 0
    for node in _walk(root):
        kept = []
        for child in node.children:
            if child.atom is None and child.head() == parent_head and child.child_list(child_head):
                removed += 1
            else:
                kept.append(child)
        node.children = kept
    return removed

def replace_atom_values_in_parents(root, parents, old, new):
    changed = 0
    for node in _walk(root):
        if node.head() in parents:
            for child in node.children:
                if child.atom is not None and child.atom == old:
                    child.atom = new
                    changed += 1
    return changed

def downgrade_teardrop_curved_edges(root):
    changed = rename_child_head_in_parents(root, {'teardrops'}, 'curved_edges', 'curve_points')
    changed += replace_atom_values_in_parents(root, {'curve_points'}, 'no', '0')
    changed += replace_atom_values_in_parents(root, {'curve_points'}, 'false', '0')
    changed += replace_atom_values_in_parents(root, {'curve_points'}, 'yes', '5')
    changed += replace_atom_values_in_parents(root, {'curve_points'}, 'true', '5')
    return changed

def _child_float(node, head, default):
    child = node.child_list(head)
    if not child:
        return default
    value = _to_float(child.atom_at(1))
    return default if value is None else value

def _dimension_points(node):
    pts = node.child_list('pts')
    if not pts:
        return None
    points = []
    for child in pts.children:
        if child.atom is None and child.head() == 'xy':
            x = _to_float(child.atom_at(1))
            y = _to_float(child.atom_at(2))
            if x is not None and y is not None:
                points.append((x, y))
    if len(points) < 2:
        return None
    return (points[0], points[1])

def _xy_node(point):
    return sexpr_list(atom('xy'), atom(_format_float(point[0])), atom(_format_float(point[1])))

def _pts_node(start, end):
    return sexpr_list(atom('pts'), _xy_node(start), _xy_node(end))

def _legacy_dimension_line(head, start, end):
    return sexpr_list(atom(head), _pts_node(start, end))

def _transform_point_if_needed(point, transform):
    if not transform:
        return point
    return _point_to_footprint_local(point[0], point[1], transform)

def _clone_atom_node(node):
    return atom(node.atom or '', node.quoted)

def _copy_dimension_layer(source, text):
    layer = source.child_list('layer') or (text.child_list('layer') if text else None)
    if layer and len(layer.children) > 1 and (layer.children[1].atom is not None):
        return sexpr_list(atom('layer'), _clone_atom_node(layer.children[1]))
    return sexpr_list(atom('layer'), atom('Dwgs.User', True))

def _copy_dimension_tstamp(source, text):
    tstamp = source.child_list('tstamp') or source.child_list('uuid')
    if not tstamp and text:
        tstamp = text.child_list('tstamp') or text.child_list('uuid')
    if tstamp and len(tstamp.children) > 1 and (tstamp.children[1].atom is not None):
        return sexpr_list(atom('tstamp'), _clone_atom_node(tstamp.children[1]))
    return None

def _legacy_dimension_from_modern(node, transform):
    points = _dimension_points(node)
    source_text = node.child_list('gr_text')
    if not points or not source_text:
        return None
    p1, p2 = points
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    length = math.hypot(dx, dy)
    if length <= 0:
        return None
    unit = (dx / length, dy / length)
    perpendicular = (-unit[1], unit[0])
    height = _child_float(node, 'height', 0.0)
    style = node.child_list('style') or sexpr_list(atom('style'))
    thickness = _child_float(style, 'thickness', 0.15)
    arrow_length = _child_float(style, 'arrow_length', 1.27)
    extension_height = _child_float(style, 'extension_height', 0.58642)
    extension_offset = _child_float(style, 'extension_offset', 0.5)
    height_sign = -1.0 if height < 0 else 1.0

    def offset(point, distance):
        return (point[0] + perpendicular[0] * distance, point[1] + perpendicular[1] * distance)
    feature1_start = p1
    feature1_end = offset(p1, height + extension_height * height_sign)
    feature2_start = p2
    feature2_end = offset(p2, height + extension_height * height_sign)
    crossbar1 = offset(p1, height)
    crossbar2 = offset(p2, height)
    arrow_angle = math.radians(27.5)
    arrow_along = arrow_length * math.cos(arrow_angle)
    arrow_side = arrow_length * math.sin(arrow_angle)

    def arrow_points(origin, direction, side):
        return (origin[0] + direction[0] * arrow_along + perpendicular[0] * side, origin[1] + direction[1] * arrow_along + perpendicular[1] * side)
    arrow1a = arrow_points(crossbar1, unit, arrow_side)
    arrow1b = arrow_points(crossbar1, unit, -arrow_side)
    arrow2a = arrow_points(crossbar2, (-unit[0], -unit[1]), arrow_side)
    arrow2b = arrow_points(crossbar2, (-unit[0], -unit[1]), -arrow_side)
    text = source_text
    if transform:
        _transform_dimension_text_to_footprint_local(text, transform)
    legacy = sexpr_list(atom('dimension'))
    legacy.children.append(sexpr_list(atom('width'), atom(_format_float(thickness))))
    legacy.children.append(_copy_dimension_layer(node, text))
    tstamp = _copy_dimension_tstamp(node, text)
    if tstamp:
        legacy.children.append(tstamp)
    legacy.children.append(text)
    legacy.children.append(_legacy_dimension_line('feature1', _transform_point_if_needed(feature1_start, transform), _transform_point_if_needed(feature1_end, transform)))
    legacy.children.append(_legacy_dimension_line('feature2', _transform_point_if_needed(feature2_start, transform), _transform_point_if_needed(feature2_end, transform)))
    legacy.children.append(_legacy_dimension_line('crossbar', _transform_point_if_needed(crossbar2, transform), _transform_point_if_needed(crossbar1, transform)))
    legacy.children.append(_legacy_dimension_line('arrow1a', _transform_point_if_needed(crossbar1, transform), _transform_point_if_needed(arrow1a, transform)))
    legacy.children.append(_legacy_dimension_line('arrow1b', _transform_point_if_needed(crossbar1, transform), _transform_point_if_needed(arrow1b, transform)))
    legacy.children.append(_legacy_dimension_line('arrow2a', _transform_point_if_needed(crossbar2, transform), _transform_point_if_needed(arrow2a, transform)))
    legacy.children.append(_legacy_dimension_line('arrow2b', _transform_point_if_needed(crossbar2, transform), _transform_point_if_needed(arrow2b, transform)))
    return legacy

def _graphic_line(start, end, layer, width):
    return sexpr_list(atom('gr_line'), sexpr_list(atom('start'), atom(_format_float(start[0])), atom(_format_float(start[1]))), sexpr_list(atom('end'), atom(_format_float(end[0])), atom(_format_float(end[1]))), sexpr_list(atom('stroke'), sexpr_list(atom('width'), atom(_format_float(width))), sexpr_list(atom('type'), atom('default'))), layer)

def _dimension_graphics_from_modern(node):
    points = _dimension_points(node)
    source_text = node.child_list('gr_text')
    if not points or not source_text:
        return []
    p1, p2 = points
    dim_type = node.child_list('type').atom_at(1) if node.child_list('type') else 'aligned'
    style = node.child_list('style') or sexpr_list(atom('style'))
    thickness = _child_float(style, 'thickness', 0.15)
    arrow_length = _child_float(style, 'arrow_length', 1.27)
    height = _child_float(node, 'height', 0.0)
    layer = _copy_dimension_layer(node, source_text)

    def line(start, end):
        return _graphic_line(start, end, _copy_dimension_layer(node, source_text), thickness)

    def arrow_lines(origin, direction, perpendicular):
        arrow_angle = math.radians(27.5)
        arrow_along = arrow_length * math.cos(arrow_angle)
        arrow_side = arrow_length * math.sin(arrow_angle)

        def endpoint(side):
            return (origin[0] + direction[0] * arrow_along + perpendicular[0] * side, origin[1] + direction[1] * arrow_along + perpendicular[1] * side)
        return [line(origin, endpoint(arrow_side)), line(origin, endpoint(-arrow_side))]
    if dim_type == 'orthogonal':
        orientation = _to_int(node.child_list('orientation').atom_at(1), 0) if node.child_list('orientation') else 0
        extension_height = _child_float(style, 'extension_height', 0.58642)
        height_sign = -1.0 if height < 0 else 1.0
        if orientation == 1:
            crossbar1 = (p1[0] + height, p1[1])
            crossbar2 = (p1[0] + height, p2[1])
            feature1_end = (p1[0] + height + extension_height * height_sign, p1[1])
            feature2_end = (p1[0] + height + extension_height * height_sign, p2[1])
            direction1 = (0.0, -1.0 if p2[1] < p1[1] else 1.0)
            direction2 = (-direction1[0], -direction1[1])
            perpendicular = (1.0, 0.0)
        else:
            crossbar1 = (p1[0], p1[1] + height)
            crossbar2 = (p2[0], p1[1] + height)
            feature1_end = (p1[0], p1[1] + height + extension_height * height_sign)
            feature2_end = (p2[0], p1[1] + height + extension_height * height_sign)
            direction1 = (1.0 if p2[0] > p1[0] else -1.0, 0.0)
            direction2 = (-direction1[0], -direction1[1])
            perpendicular = (0.0, 1.0)
        return [source_text, line(p1, feature1_end), line(p2, feature2_end), line(crossbar1, crossbar2), *arrow_lines(crossbar1, direction1, perpendicular), *arrow_lines(crossbar2, direction2, perpendicular)]
    if dim_type in {'radial', 'leader'}:
        return [source_text, _graphic_line(p1, p2, layer, thickness)]
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    length = math.hypot(dx, dy)
    if length <= 0:
        return [source_text]
    unit = (dx / length, dy / length)
    perpendicular = (-unit[1], unit[0])
    extension_height = _child_float(style, 'extension_height', 0.58642)

    def offset(point, distance):
        return (point[0] + perpendicular[0] * distance, point[1] + perpendicular[1] * distance)
    height_sign = -1.0 if height < 0 else 1.0
    feature1_end = offset(p1, height + extension_height * height_sign)
    feature2_end = offset(p2, height + extension_height * height_sign)
    crossbar1 = offset(p1, height)
    crossbar2 = offset(p2, height)
    return [source_text, _graphic_line(p1, feature1_end, _copy_dimension_layer(node, source_text), thickness), _graphic_line(p2, feature2_end, _copy_dimension_layer(node, source_text), thickness), _graphic_line(crossbar1, crossbar2, _copy_dimension_layer(node, source_text), thickness), *arrow_lines(crossbar1, unit, perpendicular), *arrow_lines(crossbar2, (-unit[0], -unit[1]), perpendicular)]

def downgrade_dimensions_to_graphics(root):
    graphics = []

    def convert(node):
        changed = 0
        kept = []
        for child in node.children:
            if child.atom is None and child.head() == 'dimension':
                converted = _dimension_graphics_from_modern(child)
                if converted:
                    graphics.extend(converted)
                changed += 1
            else:
                if child.atom is None:
                    changed += convert(child)
                kept.append(child)
        node.children = kept
        return changed
    changed = convert(root)
    if graphics and root.head() == 'kicad_pcb':
        root.children.extend(graphics)
    return changed

def downgrade_dimensions_to_legacy(root):
    lifted_dimensions = []

    def convert(node, inside_footprint, footprint_transform):
        inside = inside_footprint or node.head() in {'footprint', 'module'}
        current_transform = footprint_transform
        if node.head() in {'footprint', 'module'}:
            current_transform = _footprint_transform(node)
        changed = 0
        kept = []
        for child in node.children:
            if child.atom is None and child.head() == 'dimension':
                legacy = _legacy_dimension_from_modern(child, None)
                if legacy:
                    if inside:
                        lifted_dimensions.append(legacy)
                    else:
                        kept.append(legacy)
                    changed += 1
                else:
                    changed += 1
            else:
                if child.atom is None:
                    changed += convert(child, inside, current_transform)
                kept.append(child)
        node.children = kept
        return changed
    changed = convert(root, False, None)
    if lifted_dimensions and root.head() == 'kicad_pcb':
        root.children.extend(lifted_dimensions)
    return changed

def downgrade_board_net_names_to_codes(root):
    codes = {'': 0}
    next_code = 1

    def add_name(name):
        nonlocal next_code
        if name not in codes:
            codes[name] = next_code
            next_code += 1
    for child in root.children:
        if child.atom is None and child.head() == 'net':
            if _is_int_atom(child.atom_at(1)):
                code = _to_int(child.atom_at(1))
                name = child.atom_at(2)
                codes.setdefault(name, code)
                next_code = max(next_code, code + 1)
            else:
                add_name(child.atom_at(1))
    for node in _walk(root):
        if node.head() == 'net' and (not _is_int_atom(node.atom_at(1))):
            add_name(node.atom_at(1))
    changed = 0

    def rewrite(node, parent=''):
        nonlocal changed
        if node.head() == 'net' and (not _is_int_atom(node.atom_at(1))):
            name = node.atom_at(1)
            new_children = [node.children[0], atom(str(codes.get(name, 0)))]
            if parent in {'kicad_pcb', 'pad'}:
                new_children.extend(node.children[1:])
            node.children = new_children
            changed += 1
        if node.head() == 'zone':
            net = node.child_list('net')
            if net and (not _is_int_atom(net.atom_at(1))) and (not node.child_list('net_name')):
                insert_at = len(node.children)
                for index, child in enumerate(node.children[1:], 1):
                    if child.atom is None and child.head() == 'net':
                        insert_at = index + 1
                        break
                node.children.insert(insert_at, sexpr_list(atom('net_name'), atom(net.atom_at(1), True)))
                changed += 1
        head = node.head()
        for child in node.children:
            if child.atom is None:
                rewrite(child, head)
    rewrite(root)
    existing_codes = {_to_int(c.atom_at(1)) for c in root.children if c.atom is None and c.head() == 'net' and _is_int_atom(c.atom_at(1))}
    new_entries = sorted(((name, code) for name, code in codes.items() if code not in existing_codes), key=lambda item: (item[1], item[0]))
    if new_entries and root.head() == 'kicad_pcb':
        last_net = -1
        item_heads = {'arc', 'dimension', 'footprint', 'gr_arc', 'gr_circle', 'gr_curve', 'gr_line', 'gr_poly', 'gr_rect', 'gr_text', 'group', 'image', 'segment', 'via', 'zone'}
        first_item = len(root.children)
        for i, child in enumerate(root.children):
            if child.atom is None and child.head() == 'net':
                last_net = i
            elif child.atom is None and child.head() in item_heads and (first_item == len(root.children)):
                first_item = i
        insert_at = last_net + 1 if last_net >= 0 else first_item
        for offset, (name, code) in enumerate(new_entries):
            root.children.insert(insert_at + offset, sexpr_list(atom('net'), atom(str(code)), atom(name, True)))
        changed += len(new_entries)
    return changed

def remove_introduced(root, target, rules):
    warnings = []
    for (min_version, _heads, reason), removed in remove_descendants_by_rule(root, rules, target):
        if removed:
            warnings.append(f'removed {removed} node(s) introduced in {min_version}: {reason}')
    return warnings

def _warn_if_changed(warnings, count, message):
    if count > 0:
        warnings.append(message)

def _apply_when(warnings, condition, rewrite, message):
    if condition:
        _warn_if_changed(warnings, rewrite(), message)

def _queue_child_removal(rules, condition, parents, children, message):
    if condition:
        rules.append((parents, children, message))

def _queue_descendant_removal(rules, condition, heads, message):
    if condition:
        rules.append((heads, message))

def apply_downgrade_rules(doc, target):
    root = doc.root
    warnings = []
    if doc.kind == 'symbol-library':
        child_removals = []
        warnings.extend(remove_introduced(root, target, SYMBOL_RULES))
        _apply_when(warnings, target < 20231120, lambda: remove_direct_children_by_head(root, 'generator_version'), 'removed symbol library generator_version fields')
        _apply_when(warnings, target < 20241209, lambda: remove_descendants_by_head(root, {'embedded_fonts'}), 'removed symbol library embedded_fonts fields')
        _queue_child_removal(child_removals, target < 20230409, {'symbol'}, {'exclude_from_sim'}, 'removed symbol library simulation exclusion flags')
        _apply_when(warnings, target < 20240108, lambda: downgrade_font_style_lists_to_atoms(root), 'downgraded symbol library font bold/italic bool fields')
        _queue_child_removal(child_removals, target <= 20241209, {'font'}, {'face'}, 'removed symbol library font face fields')
        if target < 20241004:
            _warn_if_changed(warnings, downgrade_bool_lists_to_atoms(root, {'hide'}), 'downgraded symbol library boolean hide fields')
            _warn_if_changed(warnings, flatten_child_lists_to_atoms_in_parents(root, {'pin_names', 'pin_numbers'}, {'hide'}), 'downgraded symbol pin visibility fields')
        _apply_when(warnings, target <= 20211014, lambda: remove_children_or_atoms_from_parents(root, {'pin'}, {'hide'}), 'removed KiCad 6-incompatible symbol pin hide fields')
        if target < 20241209:
            _warn_if_changed(warnings, ensure_legacy_property_ids(root), 'added legacy symbol property ids')
            if target <= 20211014:
                _warn_if_changed(warnings, ensure_kicad6_standard_property_ids(root), 'added KiCad 6 standard symbol property ids')
            _warn_if_changed(warnings, move_property_hide_to_effects(root), 'moved symbol property hide flags to effects')
        _queue_child_removal(child_removals, target < 20251024, {'symbol'}, {'in_pos_files'}, 'removed symbol library position file flags')
        _queue_child_removal(child_removals, target < 20250324, {'symbol'}, {'duplicate_pin_numbers_are_jumpers'}, 'removed symbol library jumper pin-number flags')
        _queue_child_removal(child_removals, target < 20250227, {'symbol'}, {'power'}, 'removed symbol library power class flags')
        _queue_child_removal(child_removals, target < 20251024, {'property'}, {'show_name', 'do_not_autoplace'}, 'removed symbol property formatting fields')
        apply_child_removal_rules(root, warnings, child_removals)
    elif doc.kind == 'schematic':
        child_removals = []
        descendant_removals = []
        warnings.extend(remove_introduced(root, target, SCHEMATIC_RULES))
        _apply_when(warnings, target < 20231120, lambda: remove_direct_children_by_head(root, 'generator_version'), 'removed schematic generator_version fields')
        _queue_descendant_removal(descendant_removals, target < 20260326, {'locked'}, 'removed schematic locked fields introduced after target version')
        _queue_descendant_removal(descendant_removals, target < 20260306, {'embedded_fonts'}, 'removed schematic embedded_fonts fields')
        _queue_descendant_removal(descendant_removals, target < 20250827, {'body_styles', 'body_style'}, 'removed schematic custom body style fields')
        apply_descendant_removal_rules(root, warnings, descendant_removals)
        _queue_child_removal(child_removals, target < 20250114, {'text', 'text_box', 'textbox'}, {'exclude_from_sim'}, 'removed schematic text simulation flags')
        _queue_child_removal(child_removals, target < 20260306, {'sheet'}, {'exclude_from_sim', 'in_bom', 'on_board', 'dnp'}, 'removed schematic sheet assembly/simulation flags')
        _apply_when(warnings, target <= 20230121, lambda: remove_descendants_by_head(root, {'exclude_from_sim'}), 'removed schematic simulation exclusion flags')
        _queue_child_removal(child_removals, target < 20220822, {'text', 'text_box', 'textbox', 'label', 'global_label', 'hierarchical_label', 'directive_label', 'netclass_flag'}, {'hyperlink'}, 'removed schematic text hyperlink fields')
        _apply_when(warnings, target < 20220914, lambda: remove_children_or_atoms_from_parents(root, {'symbol'}, {'dnp'}), 'removed schematic DNP flags')
        _apply_when(warnings, target < 20220124, lambda: rename_child_head_in_parents(root, {'kicad_sch'}, 'directive_label', 'netclass_flag'), 'renamed schematic directive labels to legacy netclass flags')
        _queue_child_removal(child_removals, target < 20251024, {'symbol'}, {'in_pos_files'}, 'removed schematic symbol position file flags')
        _queue_child_removal(child_removals, target < 20250324, {'symbol'}, {'duplicate_pin_numbers_are_jumpers'}, 'removed schematic library symbol jumper pin-number flags')
        _queue_child_removal(child_removals, target < 20250227, {'symbol'}, {'power'}, 'removed schematic library symbol power class flags')
        if target < 20241004:
            _warn_if_changed(warnings, downgrade_bool_lists_to_atoms(root, {'hide'}), 'downgraded schematic boolean hide fields')
            _warn_if_changed(warnings, flatten_child_lists_to_atoms_in_parents(root, {'pin_names', 'pin_numbers'}, {'hide'}), 'downgraded schematic symbol pin visibility fields')
        _apply_when(warnings, target <= 20211123, lambda: remove_children_or_atoms_from_parents(root, {'pin'}, {'hide'}), 'removed KiCad 6-incompatible schematic library pin hide fields')
        _apply_when(warnings, target <= 20211123, lambda: remove_children_or_atoms_from_parents(root, {'pin'}, {'alternate'}), 'removed schematic pin alternate-function fields')
        _apply_when(warnings, target < 20240108, lambda: downgrade_font_style_lists_to_atoms(root), 'downgraded schematic font bold/italic bool fields')
        _queue_child_removal(child_removals, target <= 20250114, {'font'}, {'face'}, 'removed schematic font face fields')
        _apply_when(warnings, target <= 20230121, lambda: unquote_atoms_in_headed_lists(root, {'uuid'}, 1), 'normalized schematic UUID atoms for KiCad 6/7 parsers')
        _apply_when(warnings, 20211123 < target <= 20230121, lambda: remove_placed_symbol_pin_uuid_blocks(root), 'removed KiCad 7 placed symbol pin UUID blocks')
        _apply_when(warnings, target <= 20211123, lambda: ensure_legacy_schematic_symbol_instances(root), 'generated schematic symbol instance table for KiCad 6 parsers')
        _apply_when(warnings, target <= 20211123, lambda: ensure_kicad6_standard_property_ids(root), 'added KiCad 6 standard schematic property ids')
        _apply_when(warnings, target <= 20211123, lambda: normalize_kicad6_sheet_properties(root), 'normalized KiCad 6 sheet property names and ids')
        _apply_when(warnings, target <= 20211123, lambda: remove_descendants_by_head(root, {'instances'}), 'removed schematic symbol instance data')
        if target < 20241209:
            _warn_if_changed(warnings, ensure_legacy_property_ids(root), 'added legacy schematic property ids')
            _warn_if_changed(warnings, move_property_hide_to_effects(root), 'moved schematic property hide flags to effects')
        _queue_child_removal(child_removals, target < 20231120, {'symbol', 'sheet'}, {'fields_autoplaced'}, 'removed schematic symbol/sheet fields_autoplaced fields')
        _queue_child_removal(child_removals, target < 20251028, {'property'}, {'show_name', 'do_not_autoplace'}, 'removed schematic property formatting fields')
        _apply_when(warnings, target < 20260306, lambda: remove_direct_children_by_head(root, 'group'), 'removed schematic group nodes')
        apply_child_removal_rules(root, warnings, child_removals)
    elif doc.kind in {'board', 'footprint'}:
        child_removals = []
        child_value_rewrites = []
        descendant_removals = []
        containing_child_removals = []
        warnings.extend(remove_introduced(root, target, BOARD_RULES))
        if target < 20260410:
            containing_child_removals.append(('model', 'type', 'removed typed/extruded 3D model blocks'))
        _queue_descendant_removal(descendant_removals, target < 20250228, {'covering', 'plugging', 'filling', 'capping'}, 'removed IPC-4761 via protection fields')
        _queue_descendant_removal(descendant_removals, target < 20231212, {'unlocked'}, 'removed PCB text keep-upright unlock fields')
        apply_structural_removal_rules(root, warnings, descendant_removals, containing_child_removals)
        _apply_when(warnings, target < 20260513, lambda: replace_atom_values_in_parents(root, {'mode'}, 'thieving', 'polygon'), 'downgraded copper thieving fill modes to polygon fill')
        _queue_child_removal(child_removals, target >= 20220225, {'footprint', 'module'}, {'tedit'}, 'removed obsolete footprint tedit fields')
        _queue_child_removal(child_removals, target >= 20200628, {'setup'}, {'visible_elements'}, 'removed obsolete board visible_elements settings')
        _queue_child_removal(child_removals, target < 20240108, {'setup'}, {'allow_soldermask_bridges_in_footprints'}, 'removed board soldermask bridge setup fields')
        _apply_when(warnings, target < 20240703, lambda: downgrade_user_layer_types(root), 'removed user-layer type qualifiers')
        if doc.kind == 'board':
            _apply_when(warnings, 20171130 < target < 20260603, lambda: downgrade_pcb_user_layers_to_fixed(root), 'mapped modern PCB user layers to fixed legacy user layers')
        if target < 20241010:
            _queue_child_removal(child_removals, True, {'gr_line', 'gr_arc', 'gr_circle', 'gr_rect', 'gr_poly', 'fp_line', 'fp_arc', 'fp_circle', 'fp_rect', 'fp_poly'}, {'solder_mask_margin'}, 'removed graphic solder_mask_margin fields')
        if target < 20241030:
            _queue_child_removal(child_removals, True, {'style'}, {'arrow_direction'}, 'removed dimension arrow direction fields')
        _queue_child_removal(child_removals, target < 20260603, {'table_cell'}, {'knockout'}, 'removed PCB table-cell knockout flags')
        _queue_child_removal(child_removals, target < 20250210, {'gr_text', 'fp_text'}, {'render_cache'}, 'removed PCB text render caches')
        _queue_child_removal(child_removals, target < 20241009, {'zone'}, {'placement'}, 'removed zone placement fields')
        _queue_child_removal(child_removals, target <= 20221018, {'zone'}, {'attr'}, 'removed zone attr fields')
        _queue_child_removal(child_removals, target < 20241007, {'segment', 'arc'}, {'solder_mask_margin', 'solder_mask_layer'}, 'removed track soldermask layer/margin fields')
        _queue_child_removal(child_removals, target < 20240617, {'table_cell'}, {'angle'}, 'removed PCB table cell angle fields')
        _queue_child_removal(child_removals, target < 20260521, {'pad'}, {'sim_electrical_type'}, 'removed pad simulation electrical type fields')
        if target < 20250228:
            _warn_if_changed(warnings, downgrade_tenting_to_legacy_atoms(root), 'downgraded tenting front/back bool lists to legacy atom syntax')
        _apply_when(warnings, target < 20241228, lambda: downgrade_teardrop_curved_edges(root), 'downgraded teardrop curved-edge fields to legacy curve point counts')
        if target < 20231212:
            _warn_if_changed(warnings, downgrade_boolean_presence_nodes(root, {'locked', 'hide'}), 'downgraded board/footprint boolean locked/hide fields')
            _queue_child_removal(child_removals, True, {'model'}, {'hide'}, 'removed legacy-incompatible 3D model hide fields')
        _apply_when(warnings, target < 20231014, lambda: remove_direct_children_by_head(root, 'generator_version'), 'removed board/footprint generator_version fields')
        if target < 20230924:
            _warn_if_changed(warnings, downgrade_pcbplotparams_bools(root), 'downgraded pcbplotparams boolean values')
            _warn_if_changed(warnings, downgrade_shape_fill_no_to_none(root), 'downgraded PCB shape fill no values to none')
        if target < 20230730:
            _queue_child_removal(child_removals, True, {'gr_line', 'gr_arc', 'gr_circle', 'gr_poly', 'gr_curve', 'fp_line', 'fp_arc', 'fp_circle', 'fp_poly', 'fp_curve'}, {'net'}, 'removed PCB graphic shape net connectivity fields')
        if target < 20230730 and target > 20171130:
            _queue_child_removal(child_removals, True, {'gr_rect', 'fp_rect'}, {'net'}, 'removed PCB graphic rectangle net connectivity fields')
        if target < 20240108:
            _queue_child_removal(child_removals, True, {'group'}, {'locked'}, 'removed group locked fields')
            child_value_rewrites.append(('bool-list', {'font'}, {'bold', 'italic'}, 'downgraded PCB font bold/italic bool fields'))
        if target <= 20171130:
            _queue_child_removal(child_removals, True, {'footprint', 'module'}, {'group'}, 'removed footprint group metadata for KiCad 5')
            _queue_child_removal(child_removals, True, {'footprint', 'module'}, {'zone'}, 'removed footprint keepout zones for KiCad 5')
        _apply_when(warnings, target < 20230620, lambda: downgrade_pcb_footprint_fields(root), 'downgraded PCB footprint fields to legacy storage')
        if target < 20240225:
            _warn_if_changed(warnings, rename_child_head_in_parents(root, {'footprint', 'module', 'pad'}, 'solder_paste_margin_ratio', 'solder_paste_ratio'), 'renamed solder_paste_margin_ratio fields to legacy solder_paste_ratio')
        if target <= 20221018:
            _warn_if_changed(warnings, rename_child_head_in_parents(root, {'pad', 'zone'}, 'thermal_bridge_width', 'thermal_width'), 'renamed thermal_bridge_width fields to legacy thermal_width')
            _warn_if_changed(warnings, downgrade_pcb_stroke_to_legacy_width(root), 'downgraded PCB stroke blocks to legacy width fields')
        if target < 20240108:
            _queue_child_removal(child_removals, True, {'via'}, {'remove_unused_layers', 'keep_end_layers', 'start_end_only', 'zone_layer_connections'}, 'removed legacy via layer-connection fields')
        if target < 20231231:
            parents = {'footprint', 'module', 'pad', 'via', 'segment', 'arc', 'zone', 'gr_line', 'gr_arc', 'gr_circle', 'gr_rect', 'gr_poly', 'gr_curve', 'gr_text', 'fp_line', 'fp_arc', 'fp_circle', 'fp_rect', 'fp_poly', 'fp_curve', 'fp_text'}
            _warn_if_changed(warnings, rename_child_head_in_parents(root, parents, 'uuid', 'tstamp'), 'renamed footprint uuid fields back to legacy tstamp')
            _warn_if_changed(warnings, rename_child_head_in_parents(root, {'group', 'generated'}, 'uuid', 'id'), 'renamed board group/generated uuid fields back to id')
            _warn_if_changed(warnings, unquote_atoms_in_headed_lists(root, {'uuid', 'tstamp', 'id'}, 1), 'normalized PCB UUID/tstamp/id atoms for legacy parsers')
        _queue_child_removal(child_removals, target < 20250324, {'footprint'}, {'duplicate_pad_numbers_are_jumpers', 'jumper_pad_groups'}, 'removed footprint jumper pad fields')
        _queue_child_removal(child_removals, target <= 20221018, {'footprint', 'module'}, {'net_tie_pad_groups'}, 'removed footprint net-tie pad group fields')
        _queue_child_removal(child_removals, target < 20250909, {'footprint', 'module'}, {'units'}, 'removed footprint unit pin grouping fields')
        _apply_when(warnings, target <= 20221018, lambda: remove_atoms_from_headed_lists(root, {'attr'}, {'dnp'}), 'removed footprint dnp attributes')
        _apply_when(warnings, target <= 20221018, lambda: remove_atoms_from_headed_lists(root, {'attr'}, {'allow_missing_courtyard'}), 'removed legacy-incompatible footprint attr flags')
        _queue_child_removal(child_removals, target < 20250309, {'placement'}, {'component_class'}, 'removed rule_area component_class placement sources')
        _apply_when(warnings, target < 20250222, lambda: downgrade_shape_hatch_fills(root), 'downgraded PCB shape hatch fills')
        _queue_child_removal(child_removals, target < 20250210, {'gr_text_box', 'fp_text_box'}, {'knockout'}, 'removed PCB text box knockout fields')
        _apply_when(warnings, target < 20250210, lambda: ensure_zone_filled_areas_thickness(root), 'tagged cached zone fills as polygon fills')
        _apply_when(warnings, target < 20250210, lambda: remove_atoms_from_headed_lists(root, {'layer'}, {'knockout'}), 'removed PCB layer knockout flags')
        _queue_child_removal(child_removals, target <= 20241229, {'font'}, {'face'}, 'removed PCB font face fields')
        if target <= 20221018:
            child_value_rewrites.append(('presence-bool', None, {'free'}, 'downgraded free via fields'))
        if target <= 20221018:
            _queue_child_removal(child_removals, True, {'pad', 'via'}, {'remove_unused_layers'}, 'removed pad/via remove_unused_layers fields')
            _queue_child_removal(child_removals, True, {'pad', 'zone'}, {'thermal_bridge_angle'}, 'removed pad/zone thermal bridge angle fields')
        if target <= 20171130:
            _warn_if_changed(warnings, remove_atoms_from_headed_lists(root, {'via'}, {'free'}), 'removed free via atoms for KiCad 5')
            _queue_child_removal(child_removals, True, {'via'}, {'free'}, 'removed free via fields for KiCad 5')
            _queue_child_removal(child_removals, True, {'gr_circle', 'gr_poly', 'fp_circle', 'fp_poly'}, {'fill'}, 'removed PCB graphic fill fields for KiCad 5')
            _queue_child_removal(child_removals, True, {'pad'}, {'chamfer', 'chamfer_ratio', 'pinfunction', 'pintype', 'property', 'tstamp', 'uuid'}, 'removed pad fields for KiCad 5')
            _queue_child_removal(child_removals, True, {'model'}, {'opacity'}, 'removed 3D model opacity fields for KiCad 5')
        if target < 20160815:
            _queue_child_removal(child_removals, True, {'net_class'}, {'diff_pair_width', 'diff_pair_gap', 'diff_pair_via_gap'}, 'removed netclass differential-pair constraints for KiCad 4')
        if target < 20170922:
            _queue_child_removal(child_removals, True, {'zone'}, {'keepout'}, 'removed multilayer keepout settings for KiCad 4')
        if target < 20241030:
            child_value_rewrites.insert(0, ('bool-list', None, {'suppress_zeroes', 'keep_text_aligned'}, 'downgraded dimension boolean fields to legacy atom syntax'))
        apply_child_value_rewrite_rules(root, warnings, child_value_rewrites)
        if target <= 20221018:
            legacy_locked_atom_parents = {'footprint', 'module', 'pad', 'via', 'segment', 'arc', 'zone', 'group', 'generated', 'gr_line', 'gr_arc', 'gr_circle', 'gr_rect', 'gr_poly', 'gr_curve', 'gr_text', 'fp_line', 'fp_arc', 'fp_circle', 'fp_rect', 'fp_poly', 'fp_curve', 'fp_text', 'dimension'}
            _warn_if_changed(warnings, remove_atoms_from_headed_lists(root, legacy_locked_atom_parents, {'locked'}), 'removed legacy-incompatible locked atoms')
            _warn_if_changed(warnings, downgrade_dimensions_to_graphics(root), 'downgraded PCB dimensions to legacy graphic annotations')
            _warn_if_changed(warnings, remove_descendants_by_head(root, {'locked'}), 'removed legacy-incompatible locked fields')
            _warn_if_changed(warnings, downgrade_pcb_stroke_to_legacy_width(root), 'downgraded generated PCB dimension strokes to legacy width fields')
        if target <= 20171130:
            _warn_if_changed(warnings, remove_children_from_parents(root, {'footprint', 'module'}, {'property'}), 'removed footprint properties for KiCad 5')
            _warn_if_changed(warnings, remove_children_from_parents(root, {'footprint', 'module'}, {'attr'}), 'removed footprint attributes for KiCad 5')
            _warn_if_changed(warnings, remove_children_from_parents(root, {'fp_text'}, {'tstamp', 'uuid'}), 'removed footprint text ids for KiCad 5')
            _warn_if_changed(warnings, downgrade_pcb_header_to_legacy5(root), 'downgraded PCB header and layer syntax to KiCad 5 format')
            _warn_if_changed(warnings, downgrade_layer_refs_to_legacy5(root), 'mapped modern/custom PCB user layers to KiCad 5 fixed user layers')
            _warn_if_changed(warnings, split_multilayer_zones_to_legacy_single_layer_zones(root), 'split multilayer PCB zones into KiCad 5 single-layer zones')
            _warn_if_changed(warnings, remove_nodes_containing_child(root, 'zone', 'keepout'), 'removed keepout zones for KiCad 5')
            _warn_if_changed(warnings, remove_children_from_parents(root, {'setup'}, {'stackup'}), 'removed board stackup settings for KiCad 5')
            _warn_if_changed(warnings, rename_footprints_to_modules_legacy5(root), 'renamed PCB footprint nodes to KiCad 5 module nodes')
            _warn_if_changed(warnings, downgrade_pcb_arcs_to_legacy_angles(root), 'downgraded PCB midpoint arcs to legacy angle fields for KiCad 5')
            _warn_if_changed(warnings, downgrade_pcb_rects_to_legacy_lines(root), 'downgraded PCB rectangles to legacy line segments for KiCad 5')
            _warn_if_changed(warnings, downgrade_pcb_track_arcs_to_segments(root), 'approximated PCB track arcs with legacy segments for KiCad 5')
            _warn_if_changed(warnings, remove_children_from_parents(root, {'filled_polygon'}, {'layer'}), 'removed filled polygon layer fields for KiCad 5')
            _warn_if_changed(warnings, remove_children_from_parents(root, {'zone'}, {'name'}), 'removed zone name fields for KiCad 5')
            _warn_if_changed(warnings, remove_children_from_parents(root, {'zone'}, {'filled_areas_thickness'}), 'removed zone filled-area thickness fields for KiCad 5')
            _warn_if_changed(warnings, remove_children_from_parents(root, {'fill'}, {'island_removal_mode', 'island_area_min'}), 'removed zone island-removal fill fields for KiCad 5')
            _warn_if_changed(warnings, downgrade_pcb_tstamps_to_legacy5(root), 'shortened PCB UUID/tstamp atoms to KiCad 5 legacy IDs')
        if target < 20171114:
            _warn_if_changed(warnings, downgrade_model_offsets_to_legacy_at(root), 'downgraded 3D model offsets to KiCad 4 at fields')
        if target < 20170920:
            _warn_if_changed(warnings, downgrade_custom_pads_to_rects(root), 'simplified custom/rounded pads to rectangular pads for KiCad 4')
        _queue_child_removal(child_removals, target < 20251101, {'pad', 'via'}, {'front_post_machining', 'back_post_machining'}, 'removed pad/via post-machining fields')
        apply_child_removal_rules(root, warnings, child_removals)
        _apply_when(warnings, target < 20251028, lambda: downgrade_board_net_names_to_codes(root), 'added legacy netcodes to board net references')
    elif doc.kind == 'worksheet' and target < 20220228:
        warnings.extend(remove_introduced(root, target, ((20220228, ('font',), 'worksheet font blocks are not available'),)))
    return warnings

def apply_upgrade_rules(doc, target):
    root = doc.root
    warnings = []
    if target < 20211014:
        return warnings

    def warn(count, message):
        if count > 0:
            warnings.append(message)
    schematic_tstamp_parents = {'symbol', 'sheet', 'junction', 'no_connect', 'wire', 'bus', 'polyline', 'text', 'text_box', 'label', 'global_label', 'hierarchical_label', 'directive_label', 'image', 'sheet_instances', 'path', 'instance', 'property'}
    board_tstamp_parents = {'footprint', 'module', 'pad', 'via', 'segment', 'arc', 'zone', 'group', 'generated', 'gr_line', 'gr_arc', 'gr_circle', 'gr_rect', 'gr_poly', 'gr_curve', 'gr_text', 'fp_line', 'fp_arc', 'fp_circle', 'fp_rect', 'fp_poly', 'fp_curve', 'fp_text', 'dimension'}
    bool_heads = {'hide', 'bold', 'italic', 'locked', 'free', 'remove_unused_layers', 'keep_end_layers', 'suppress_zeroes', 'keep_text_aligned'}
    if doc.kind == 'symbol-library':
        if target >= 20240108:
            warn(expand_font_style_atoms(root), 'upgraded symbol library font style atoms to boolean lists')
        if target >= 20241004:
            warn(expand_presence_atoms_in_parents(root, {'pin_names', 'pin_numbers'}, {'hide'}), 'upgraded symbol pin visibility atoms to boolean lists')
        if target >= 20241209:
            warn(move_effects_hide_to_property(root), 'moved symbol property hide flags out of effects')
        warn(remove_id_from_standard_properties(root), 'removed legacy symbol property ids')
    elif doc.kind == 'schematic':
        warn(rename_child_head_in_parents(root, schematic_tstamp_parents, 'tstamp', 'uuid'), 'renamed schematic tstamp fields to uuid')
        warn(rename_child_head_in_parents(root, {'kicad_sch'}, 'netclass_flag', 'directive_label'), 'renamed schematic netclass flags to directive labels')
        warn(upgrade_text_box_start_end(root), 'upgraded schematic text box start/end fields to at/size')
        if target >= 20240108:
            warn(expand_font_style_atoms(root), 'upgraded schematic font style atoms to boolean lists')
        if target >= 20241004:
            warn(expand_presence_atoms_in_parents(root, {'pin_names', 'pin_numbers'}, {'hide'}), 'upgraded schematic symbol pin visibility atoms to boolean lists')
        if target >= 20241209:
            warn(move_effects_hide_to_property(root), 'moved schematic property hide flags out of effects')
        warn(remove_id_from_standard_properties(root), 'removed legacy schematic property ids')
    elif doc.kind in {'board', 'footprint'}:
        warn(remove_children_from_parents(root, {'kicad_pcb'}, {'host'}), 'removed legacy PCB host metadata during upgrade')
        warn(upgrade_pcb_page_to_paper(root), 'renamed legacy PCB page settings to paper')
        warn(upgrade_legacy_arc_angles(root), 'upgraded legacy PCB arc angle fields to midpoint arcs')
        warn(remove_legacy_graphic_line_angles(root), 'removed legacy PCB line angle fields')
        warn(ensure_zone_filled_areas_thickness(root), 'tagged legacy cached zone fills as polygon fills')
        warn(ensure_zone_filled_polygon_layers(root), 'added zone layers to legacy cached polygon fills')
        if target >= 20231231:
            warn(rename_child_head_in_parents(root, board_tstamp_parents, 'tstamp', 'uuid'), 'renamed PCB tstamp fields to uuid')
        warn(expand_font_style_atoms(root), 'upgraded PCB font style atoms to boolean lists')
        if target >= 20230410:
            warn(expand_presence_atoms_in_parents(root, {'attr'}, {'dnp'}), 'upgraded footprint dnp atoms to boolean lists')
        warn(normalize_bool_values(root, bool_heads), 'normalized PCB boolean values for KiCad 7 syntax')
        warn(remove_children_from_parents(root, {'footprint', 'module'}, {'tedit'}), 'removed obsolete footprint tedit fields during upgrade')
        if target >= 20251028:
            warn(upgrade_board_net_codes_to_names(root), 'upgraded legacy numeric board net references to net names')
    return warnings

def is_kicad_document_path(path):
    return path.suffix.lower() in {'.kicad_pro', '.kicad_sch', '.kicad_pcb', '.kicad_sym', '.kicad_mod', '.kicad_dru', '.kicad_wks', '.sch', '.lib', '.dcm', '.pro'}

def is_kicad_project_file_path(path):
    name = path.name.lower()
    ext = path.suffix.lower()
    if not name or name.startswith('.#') or name.endswith('~'):
        return False
    if ext in {'.bak', '.backup', '.bck', '.orig', '.tmp', '.temp'}:
        return False
    return name in {'fp-lib-table', 'sym-lib-table'} or ext in {'.kicad_pro', '.kicad_prl', '.pro', '.step', '.stp', '.wrl', '.iges', '.igs', '.stl', '.obj'} or is_kicad_document_path(path)

def is_excluded_project_dir_name(name):
    value = name.lower()
    excluded = {'.git', '.svn', '.hg', '.history', '.backup', '__pycache__', 'history', 'histories', 'backup', 'backups', 'archive', 'archives', 'old', 'gerber', 'gerbers', 'gerberfiles', 'gerber_files', 'fab', 'fabrication', 'outputs', 'production', 'plot', 'plots', 'export', 'exports', 'bom', 'ibom', 'assembly', 'jlcpcb', 'oshpark'}
    return value in excluded or 'backup' in value or 'history' in value or ('gerber' in value)

def copy_project_tree(input_path, output_path, target):
    src = input_path.resolve()
    dest = output_path.resolve()
    if src == dest:
        raise ValueError('output directory must differ from input directory')
    copied = []
    target_major = target_major_version(target)
    for path in src.rglob('*'):
        rel = path.relative_to(src)
        if any((is_excluded_project_dir_name(part) for part in rel.parts[:-1])):
            continue
        if path.is_dir():
            continue
        if not path.is_file() or not is_kicad_project_file_path(path):
            continue
        ext = path.suffix.lower()
        if target_major <= 5 and ext == '.kicad_prl':
            continue
        if target_major > 5 and ext == '.dcm' and path.with_suffix('.lib').exists():
            continue
        out = dest / rel
        if is_kicad_document_path(path):
            out = with_target_family_extension(out, target)
        out.parent.mkdir(parents=True, exist_ok=True)
        if not is_kicad_document_path(path):
            shutil.copy2(path, out)
        copied.append((path, out))
    return copied

def _report(path, kind, source_version, target_version='', changed=False, warnings=None):
    return FileReport(str(path), kind, source_version, target_version, changed, warnings)

def _replace_trailing_text(value, old, new):
    if value.lower().endswith(old.lower()):
        return value[:-len(old)] + new
    return value

def normalize_legacy_symbol_library_table_entries(root):
    if root.head() != 'sym_lib_table':
        return 0
    changed = 0
    for child in root.children:
        if child.atom is not None or child.head() != 'lib':
            continue
        type_node = child.child_list('type')
        if type_node and type_node.set_atom_at(1, 'Legacy', True):
            changed += 1
        uri = child.child_list('uri')
        if uri:
            mapped = _replace_trailing_text(uri.atom_at(1), '.kicad_sym', '.lib')
            if mapped != uri.atom_at(1) and uri.set_atom_at(1, mapped, True):
                changed += 1
    return changed

def normalize_legacy_library_table(path, target_major):
    report = _report(
        path,
        'library-table',
        'project-local',
        'legacy-compatible' if target_major <= 5 else 'modern-compatible',
    )
    try:
        text = path.read_text(encoding='utf-8-sig')
        root = parse_sexpr(text)
        changed = remove_direct_children_by_head(root, 'version')
        if target_major <= 5:
            changed += normalize_legacy_symbol_library_table_entries(root)
        if changed > 0:
            _write_text(path, format_sexpr(root))
            report.changed = True
    except Exception as exc:
        report.warnings.append('could not normalize project library table: {}'.format(exc))
    return report

def _footprint_library_nickname(lib_id):
    if ':' not in lib_id:
        return ''
    nickname = lib_id.split(':', 1)[0]
    return nickname

def _footprint_library_name(lib_id):
    if ':' not in lib_id:
        return ''
    return lib_id.split(':', 1)[1]

def collect_project_local_footprint_nicknames(project_dir, copied):
    nicknames = set()
    library_dir = project_dir / 'Library.pretty'
    if not library_dir.is_dir():
        return nicknames
    for _src, out in copied:
        if out.parent != project_dir or out.suffix.lower() != '.kicad_pcb':
            continue
        try:
            root = parse_sexpr(out.read_text(encoding='utf-8-sig'))
        except Exception:
            continue
        for node in _walk(root):
            if node.head() not in {'footprint', 'module'}:
                continue
            lib_id = node.atom_at(1)
            nickname = _footprint_library_nickname(lib_id)
            footprint_name = _footprint_library_name(lib_id)
            if nickname and footprint_name and (library_dir / (footprint_name + '.kicad_mod')).exists():
                nicknames.add(nickname)
    return nicknames

def _library_table_field(head, value):
    return sexpr_list(atom(head), atom(value, True))

def _project_local_footprint_library_entry(nickname):
    return sexpr_list(
        atom('lib'),
        _library_table_field('name', nickname),
        _library_table_field('type', 'KiCad'),
        _library_table_field('uri', '${KIPRJMOD}/Library.pretty'),
        _library_table_field('options', ''),
        _library_table_field('descr', ''),
    )

def add_project_local_footprint_library_aliases(root, nicknames):
    if root.head() != 'fp_lib_table':
        return 0
    existing = set()
    for child in root.children:
        if child.atom is None and child.head() == 'lib':
            name = child.child_list('name')
            if name:
                existing.add(name.atom_at(1))
    changed = 0
    for nickname in sorted(nicknames):
        if nickname in existing:
            continue
        root.children.append(_project_local_footprint_library_entry(nickname))
        existing.add(nickname)
        changed += 1
    return changed

def ensure_legacy_footprint_library_aliases(table_path, copied, target_major):
    warnings = []
    if target_major > 5 or table_path.name.lower() != 'fp-lib-table':
        return (0, warnings)
    project_dir = table_path.parent
    nicknames = collect_project_local_footprint_nicknames(project_dir, copied)
    if not nicknames:
        return (0, warnings)
    try:
        root = parse_sexpr(table_path.read_text(encoding='utf-8-sig'))
        changed = add_project_local_footprint_library_aliases(root, nicknames)
        if changed > 0:
            _write_text(table_path, format_sexpr(root))
        return (changed, warnings)
    except Exception as exc:
        warnings.append('could not add project-local footprint aliases: {}'.format(exc))
        return (0, warnings)

def normalize_project_library_tables(copied, target_major):
    reports = []
    for _src, out in copied:
        if out.name.lower() not in {'fp-lib-table', 'sym-lib-table'}:
            continue
        alias_changes, alias_warnings = ensure_legacy_footprint_library_aliases(out, copied, target_major)
        report = normalize_legacy_library_table(out, target_major)
        report.changed = report.changed or alias_changes > 0
        report.warnings.extend(alias_warnings)
        reports.append(report)
    return reports

def _clone_node(node):
    if node.atom is not None:
        return Node(atom=node.atom, quoted=node.quoted)
    return Node(children=[_clone_node(child) for child in node.children])

def _project_library_uri(project_dir, library_path):
    try:
        rel = library_path.relative_to(project_dir)
    except ValueError:
        rel = library_path.name
    return '${KIPRJMOD}/' + (rel.as_posix() if hasattr(rel, 'as_posix') else str(rel).replace('\\', '/'))

def _symbol_library_nickname_from_lib_id(lib_id):
    if ':' not in lib_id:
        return ''
    nickname = lib_id.split(':', 1)[0]
    return nickname if nickname else ''

def _symbol_library_symbol_name_from_lib_id(lib_id):
    if ':' not in lib_id:
        return ''
    name = lib_id.split(':', 1)[1]
    return name if name else ''

def _collect_schematic_lib_ids(root):
    lib_ids = set()
    for node in _walk(root):
        if node.head() != 'symbol':
            continue
        lib_id = _child_atom_or_empty(node, 'lib_id')
        if lib_id:
            lib_ids.add(lib_id)
    return lib_ids

def _collect_referenced_schematic_library_nicknames(project_dir, copied):
    nicknames = set()
    for _src, out in copied:
        if out.parent != project_dir or out.suffix.lower() != '.kicad_sch':
            continue
        try:
            root = parse_sexpr(out.read_text(encoding='utf-8-sig'))
        except Exception:
            continue
        for lib_id in _collect_schematic_lib_ids(root):
            nickname = _symbol_library_nickname_from_lib_id(lib_id)
            if nickname:
                nicknames.add(nickname)
    return nicknames

def _collect_project_local_symbol_libraries(project_dir, copied, allowed=None, filter_names=False):
    libraries = {}
    allowed = set() if allowed is None else allowed
    for _src, out in copied:
        if out.parent != project_dir or out.suffix.lower() != '.kicad_sym':
            continue
        nickname = out.stem
        if filter_names and nickname not in allowed:
            continue
        libraries[nickname] = _project_library_uri(project_dir, out)
    return libraries

def _project_local_symbol_library_entry(nickname, uri):
    return sexpr_list(
        atom('lib'),
        _library_table_field('name', nickname),
        _library_table_field('type', 'KiCad'),
        _library_table_field('uri', uri),
        _library_table_field('options', ''),
        _library_table_field('descr', ''),
    )

def _add_project_local_symbol_libraries(root, libraries):
    if root.head() != 'sym_lib_table':
        return 0
    existing = {}
    for child in root.children:
        if child.atom is None and child.head() == 'lib':
            name = _child_atom_or_empty(child, 'name')
            if name:
                existing[name] = child
    changed = 0
    for nickname in sorted(libraries):
        uri_value = libraries[nickname]
        lib = existing.get(nickname)
        if lib:
            type_node = lib.child_list('type')
            if type_node:
                if type_node.set_atom_at(1, 'KiCad', True):
                    changed += 1
            else:
                lib.children.append(_library_table_field('type', 'KiCad'))
                changed += 1
            uri_node = lib.child_list('uri')
            if uri_node:
                if uri_node.set_atom_at(1, uri_value, True):
                    changed += 1
            else:
                lib.children.append(_library_table_field('uri', uri_value))
                changed += 1
            continue
        root.children.append(_project_local_symbol_library_entry(nickname, uri_value))
        existing[nickname] = root.children[-1]
        changed += 1
    return changed

def ensure_project_local_symbol_library_table(project_dir, copied, target_major):
    table_path = project_dir / 'sym-lib-table'
    report = _report(table_path, 'library-table', 'project-local', 'modern-compatible')
    referenced = _collect_referenced_schematic_library_nicknames(project_dir, copied) if target_major > 5 else set()
    libraries = _collect_project_local_symbol_libraries(project_dir, copied, referenced, target_major > 5)
    if not libraries:
        return report
    try:
        root = sexpr_list(atom('sym_lib_table'))
        if target_major >= 7:
            root.children.append(sexpr_list(atom('version'), atom('7')))
        changed = _add_project_local_symbol_libraries(root, libraries)
        if changed > 0 or target_major > 5 or not table_path.exists():
            _write_text(table_path, format_sexpr(root))
            report.changed = True
            report.warnings.append('wrote project-local symbol library table for generated .kicad_sym files')
    except Exception as exc:
        report.warnings.append('could not write project-local symbol library table: {}'.format(exc))
    return report

def _collect_project_local_symbol_library_paths(project_dir, copied):
    libraries = {}
    for _src, out in copied:
        if out.parent == project_dir and out.suffix.lower() == '.kicad_sym':
            libraries[out.stem] = out
    return libraries

def _symbol_maps_by_library(project_dir, copied, warnings):
    result = {}
    for nickname, path in _collect_project_local_symbol_library_paths(project_dir, copied).items():
        try:
            root = parse_sexpr(path.read_text(encoding='utf-8-sig'))
        except Exception as exc:
            warnings.append('could not read generated symbol library {}: {}'.format(path, exc))
            continue
        if root.head() != 'kicad_symbol_lib':
            continue
        symbols = {}
        for child in root.children:
            if child.atom is None and child.head() == 'symbol':
                name = child.atom_at(1)
                if name:
                    symbols[name] = _clone_node(child)
        result[nickname] = symbols
    return result

def _resolve_project_local_symbol_source(symbols_by_library, nickname, symbol_name, visiting=None):
    if visiting is None:
        visiting = set()
    lib_id = nickname + ':' + symbol_name if nickname and symbol_name else ''
    if not lib_id or lib_id in visiting:
        return None
    library = symbols_by_library.get(nickname)
    if not library or symbol_name not in library:
        return None
    symbol = library[symbol_name]
    extends = symbol.child_list('extends')
    if not extends or not extends.atom_at(1):
        return symbol
    parent_nickname = nickname
    parent_name = extends.atom_at(1)
    if ':' in parent_name:
        parent_nickname, parent_name = parent_name.split(':', 1)
    visiting.add(lib_id)
    parent = _resolve_project_local_symbol_source(symbols_by_library, parent_nickname, parent_name, visiting)
    visiting.remove(lib_id)
    return parent or symbol

def _rename_nested_symbol_definitions(node, old_name, new_name):
    if not node or not old_name or not new_name:
        return
    for child in node.children:
        if child.atom is not None:
            continue
        if child.head() == 'symbol':
            name = child.atom_at(1)
            if len(name) > len(old_name) and name.startswith(old_name) and name[len(old_name)] == '_':
                child.set_atom_at(1, new_name + name[len(old_name):], True)
            extends = child.child_list('extends')
            if extends:
                parent = extends.atom_at(1)
                if len(parent) > len(old_name) and parent.startswith(old_name) and parent[len(old_name)] == '_':
                    extends.set_atom_at(1, new_name + parent[len(old_name):], True)
        _rename_nested_symbol_definitions(child, old_name, new_name)

def _set_symbol_value_property(symbol, value):
    for child in symbol.children:
        if child.atom is None and child.head() == 'property' and child.atom_at(1) == 'Value':
            child.set_atom_at(2, value, True)
            return

def _ensure_schematic_lib_symbols_node(root):
    if root.head() != 'kicad_sch':
        return None
    existing = root.child_list('lib_symbols')
    if existing:
        existing.children = [atom('lib_symbols')]
        return existing
    lib_symbols = sexpr_list(atom('lib_symbols'))
    insert_at = min(4, len(root.children))
    root.children.insert(insert_at, lib_symbols)
    return lib_symbols

def embed_project_local_schematic_symbols(project_dir, copied, warnings):
    symbols_by_library = _symbol_maps_by_library(project_dir, copied, warnings)
    if not symbols_by_library:
        return 0
    changed = 0
    for _src, out in copied:
        if out.parent != project_dir or out.suffix.lower() != '.kicad_sch':
            continue
        try:
            text = out.read_text(encoding='utf-8-sig')
            root = parse_sexpr(text)
            lib_ids = _collect_schematic_lib_ids(root)
            lib_symbols = _ensure_schematic_lib_symbols_node(root)
            if not lib_symbols:
                continue
            added = 0
            embedded = set()
            for lib_id in sorted(lib_ids):
                nickname = _symbol_library_nickname_from_lib_id(lib_id)
                symbol_name = _symbol_library_symbol_name_from_lib_id(lib_id)
                if not nickname or not symbol_name or lib_id in embedded:
                    continue
                source = _resolve_project_local_symbol_source(symbols_by_library, nickname, symbol_name)
                if not source:
                    continue
                clone = _clone_node(source)
                remove_direct_children_by_head(clone, 'extends')
                old_name = clone.atom_at(1)
                if clone.set_atom_at(1, lib_id, True):
                    _rename_nested_symbol_definitions(clone, old_name, symbol_name)
                    _set_symbol_value_property(clone, symbol_name)
                    lib_symbols.children.append(clone)
                    embedded.add(lib_id)
                    added += 1
            if added:
                _write_text(out, format_sexpr(root))
                changed += 1
        except Exception as exc:
            warnings.append('could not embed generated schematic symbols in {}: {}'.format(out, exc))
    return changed

def _append_instance_uuid(prefix, uuid):
    if not uuid:
        return '/' if not prefix else prefix
    if not prefix or prefix == '/':
        return '/' + uuid
    return prefix + '/' + uuid

def _normalize_legacy_sheet_path(path, root_uuid):
    if not path:
        return '/'
    if not path.startswith('/'):
        path = '/' + path
    if root_uuid:
        prefix = '/' + root_uuid
        if path == prefix:
            return '/'
        if path.startswith(prefix + '/'):
            return path[len(prefix):]
    return path

def _append_legacy_instance_uuid(sheet_path, uuid):
    if not uuid:
        return sheet_path or '/'
    if not sheet_path:
        sheet_path = '/'
    if not sheet_path.startswith('/'):
        sheet_path = '/' + sheet_path
    suffix = '/' + uuid
    if sheet_path.endswith(suffix):
        return sheet_path
    if sheet_path == '/':
        return suffix
    return sheet_path + suffix

def _sheet_instance_node(path, page):
    return sexpr_list(atom('path'), atom(path, True), sexpr_list(atom('page'), atom(page or '1', True)))

def _first_project_instance_path(node):
    instances = node.child_list('instances') if node else None
    if not instances:
        return None
    for project in instances.children:
        if project.atom is not None or project.head() != 'project':
            continue
        for child in project.children:
            if child.atom is None and child.head() == 'path':
                return child
    return None

def _normalized_hidden_instance_reference(reference, value):
    if len(reference) < 3 or not reference.startswith('#U'):
        return reference
    suffix_start = 2
    while suffix_start < len(reference) and not reference[suffix_start].isdigit():
        suffix_start += 1
    suffix = reference[suffix_start:] if suffix_start < len(reference) else ''
    if value == 'PWR_FLAG':
        return '#FLG' + suffix
    if value and (value[0] in {'+', '-'} or value in {'GND', 'VCC', 'VDD', 'VSS'}):
        return '#PWR' + suffix
    return reference

def _symbol_instance_node(path, symbol, source_path=None):
    unit = _child_atom_or_empty(source_path, 'unit') if source_path else ''
    value = _child_atom_or_empty(source_path, 'value') if source_path else ''
    footprint = _child_atom_or_empty(source_path, 'footprint') if source_path else ''
    reference = _child_atom_or_empty(source_path, 'reference') if source_path else ''
    unit = unit or _child_atom_or_empty(symbol, 'unit') or '1'
    value = value or _property_value(symbol, 'Value')
    footprint = footprint or _property_value(symbol, 'Footprint')
    reference = reference or _property_value(symbol, 'Reference')
    reference = _normalized_hidden_instance_reference(reference, value)
    return sexpr_list(
        atom('path'),
        atom(path, True),
        sexpr_list(atom('reference'), atom(reference, True)),
        sexpr_list(atom('unit'), atom(unit)),
        sexpr_list(atom('value'), atom(value, True)),
        sexpr_list(atom('footprint'), atom(footprint, True)),
    )

def _existing_sheet_instance_pages(root):
    pages = {}
    sheet_instances = root.child_list('sheet_instances') if root else None
    if not sheet_instances:
        return pages
    for child in sheet_instances.children:
        if child.atom is not None or child.head() != 'path':
            continue
        path = child.atom_at(1)
        page = _child_atom_or_empty(child, 'page')
        if path and page:
            pages[path] = page
    return pages

def _next_sheet_page(existing_pages):
    page = 2
    for value in existing_pages.values():
        try:
            page = max(page, int(value) + 1)
        except ValueError:
            pass
    return page

def _collect_existing_symbol_instances(root, build):
    symbol_instances = root.child_list('symbol_instances') if root else None
    if not symbol_instances:
        return
    for child in symbol_instances.children:
        if child.atom is not None or child.head() != 'path':
            continue
        path = child.atom_at(1)
        if path and path not in build['existing_symbols']:
            build['existing_symbols'][path] = _clone_node(child)

def _sheet_file_property_value(sheet):
    return _property_value(sheet, 'Sheet file') or _property_value(sheet, 'Sheetfile')

def _uniquified_reference(reference, duplicate_index):
    if duplicate_index <= 0 or not reference:
        return reference
    digit_start = 0
    while digit_start < len(reference) and not reference[digit_start].isdigit():
        digit_start += 1
    if digit_start >= len(reference):
        return reference + str(duplicate_index + 1)
    digit_end = digit_start
    while digit_end < len(reference) and reference[digit_end].isdigit():
        digit_end += 1
    try:
        number = int(reference[digit_start:digit_end])
    except ValueError:
        return reference + str(duplicate_index + 1)
    return reference[:digit_start] + str(number + duplicate_index * 1000) + reference[digit_end:]

def _uniquify_repeated_symbol_instance_references(symbol_instances):
    seen = {}
    used = set()
    for child in symbol_instances.children:
        if child.atom is not None or child.head() != 'path':
            continue
        reference = child.child_list('reference')
        if not reference:
            continue
        original = reference.atom_at(1)
        duplicate_index = seen.get(original, 0)
        seen[original] = duplicate_index + 1
        candidate = _uniquified_reference(original, duplicate_index)
        while candidate in used:
            duplicate_index += 1
            candidate = _uniquified_reference(original, duplicate_index)
        if candidate != original:
            reference.set_atom_at(1, candidate, True)
        used.add(candidate)

def _has_top_level_sheet(root):
    if not root:
        return False
    for child in root.children:
        if child.atom is None and child.head() == 'sheet':
            return True
    return False

def _collect_kicad6_hierarchy_instances(path, root, prefix, build):
    _collect_existing_symbol_instances(root, build)
    for child in root.children:
        if child.atom is not None or child.head() != 'symbol' or not child.child_list('lib_id'):
            continue
        uuid = _child_atom_or_empty(child, 'uuid') or _child_atom_or_empty(child, 'tstamp')
        if not uuid:
            continue
        instance_path = _append_instance_uuid(prefix, uuid)
        existing = build['existing_symbols'].get(instance_path)
        if existing:
            build['symbol_instances'].children.append(_clone_node(existing))
        else:
            build['symbol_instances'].children.append(_symbol_instance_node(instance_path, child))
    for child in root.children:
        if child.atom is not None or child.head() != 'sheet':
            continue
        uuid = _child_atom_or_empty(child, 'uuid') or _child_atom_or_empty(child, 'tstamp')
        if not uuid:
            continue
        sheet_path = _append_instance_uuid(prefix, uuid)
        if sheet_path not in build['added_sheet_paths']:
            page = build['existing_pages'].get(sheet_path)
            if not page:
                page = str(build['next_page'])
                build['next_page'] += 1
            build['sheet_instances'].children.append(_sheet_instance_node(sheet_path, page))
            build['added_sheet_paths'].add(sheet_path)
        sheet_file = _sheet_file_property_value(child)
        if not sheet_file:
            continue
        child_path = path.parent / sheet_file
        if not child_path.exists():
            continue
        active_key = str(child_path.resolve())
        if active_key in build['active_files']:
            continue
        try:
            child_root = parse_sexpr(child_path.read_text(encoding='utf-8-sig'))
        except Exception:
            continue
        build['active_files'].add(active_key)
        _collect_kicad6_hierarchy_instances(child_path, child_root, sheet_path, build)
        build['active_files'].remove(active_key)

def _replace_root_instances(root, build):
    _uniquify_repeated_symbol_instance_references(build['symbol_instances'])
    kept = []
    for child in root.children:
        if child.atom is None and child.head() in {'sheet_instances', 'symbol_instances'}:
            continue
        kept.append(child)
    kept.append(build['sheet_instances'])
    kept.append(build['symbol_instances'])
    root.children = kept

def rebuild_kicad6_hierarchy_instances(root_schematic):
    try:
        text = root_schematic.read_text(encoding='utf-8-sig')
        root = parse_sexpr(text)
    except Exception:
        return False
    if root.head() != 'kicad_sch' or not root.child_list('sheet_instances') or not _has_top_level_sheet(root):
        return False
    existing_pages = _existing_sheet_instance_pages(root)
    build = {
        'sheet_instances': sexpr_list(atom('sheet_instances')),
        'symbol_instances': sexpr_list(atom('symbol_instances')),
        'existing_pages': existing_pages,
        'existing_symbols': {},
        'added_sheet_paths': set(['/']),
        'active_files': set([str(root_schematic.resolve())]),
        'next_page': _next_sheet_page(existing_pages),
    }
    build['sheet_instances'].children.append(_sheet_instance_node('/', '1'))
    _collect_kicad6_hierarchy_instances(root_schematic, root, '', build)
    _replace_root_instances(root, build)
    _write_text(root_schematic, format_sexpr(root))
    return True

def rebuild_kicad6_project_hierarchy_instances(copied):
    changed = 0
    for _src, out in copied:
        if out.suffix.lower() == '.kicad_sch' and rebuild_kicad6_hierarchy_instances(out):
            changed += 1
    return changed

def legacy_target_version_for_kind(kind, target_major):
    if kind in {'legacy-schematic', 'schematic'}:
        return 'legacy-sch-v2' if target_major <= 4 else 'legacy-sch-v4'
    if kind in {'legacy-symbol-library', 'symbol-library'}:
        return 'legacy-lib-2.3' if target_major <= 4 else 'legacy-lib-2.4'
    if kind == 'legacy-symbol-documentation':
        return 'legacy-dcm-2.0'
    if kind in {'legacy-project', 'project'}:
        return 'legacy-pro'
    return ''

def rewrite_legacy_text_for_target(doc, target_major):
    lines = doc.raw_text.splitlines()
    warnings = []
    if doc.kind == 'legacy-schematic':
        header = 'EESchema Schematic File Version ' + ('2' if target_major <= 4 else '4')
        lines = [header if line.startswith('EESchema Schematic File Version') else line for line in lines]
        warnings.append('legacy V4/V5 rewrite preserves raw schematic records')
    elif doc.kind == 'legacy-symbol-library':
        header = 'EESchema-LIBRARY Version ' + ('2.3' if target_major <= 4 else '2.4')
        lines = [header if line.startswith('EESchema-LIBRARY Version') else line for line in lines]
        warnings.append('legacy V4/V5 rewrite preserves raw symbol records')
    return ('\n'.join(lines) + ('\n' if lines else ''), warnings)

def _legacy_split_words(line):
    out = []
    i = 0
    n = len(line)
    while i < n:
        while i < n and line[i].isspace():
            i += 1
        if i >= n:
            break
        if line[i] == '"':
            i += 1
            value = []
            while i < n:
                ch = line[i]
                i += 1
                if ch == '"':
                    break
                if ch == '\\' and i < n:
                    value.append(line[i])
                    i += 1
                else:
                    value.append(ch)
            out.append(''.join(value))
            continue
        start = i
        while i < n and not line[i].isspace():
            i += 1
        out.append(line[start:i])
    return out

def _first_legacy_quoted_value(line):
    first = line.find('"')
    if first < 0:
        return ''
    i = first + 1
    value = []
    while i < len(line):
        ch = line[i]
        i += 1
        if ch == '"':
            break
        if ch == '\\' and i < len(line):
            value.append(line[i])
            i += 1
        else:
            value.append(ch)
    return ''.join(value)

def _legacy_quoted_values(line):
    values = []
    i = 0
    while i < len(line):
        if line[i] != '"':
            i += 1
            continue
        i += 1
        value = []
        while i < len(line):
            ch = line[i]
            i += 1
            if ch == '"':
                break
            if ch == '\\' and i < len(line):
                value.append(line[i])
                i += 1
            else:
                value.append(ch)
        values.append(''.join(value))
    return values

def _legacy_coord_to_mm(value):
    parsed = _to_float(value)
    if parsed is None:
        return '0'
    return _format_float(parsed * 0.0254)

def _legacy_field_angle(orientation):
    return '90' if orientation == 'V' else '0'

def _legacy_text_angle(orientation):
    if orientation == '1':
        return '90'
    if orientation == '2':
        return '180'
    if orientation == '3':
        return '270'
    return '0'

def _legacy_library_text_angle(angle):
    return angle if _is_number(angle) else '0'

def _legacy_pin_angle(orientation):
    if orientation == 'U':
        return '90'
    if orientation == 'L':
        return '180'
    if orientation == 'D':
        return '270'
    return '0'

def _legacy_pin_type_to_sexpr(pin_type):
    return {
        'I': 'input',
        'O': 'output',
        'B': 'bidirectional',
        'T': 'tri_state',
        'W': 'power_in',
        'w': 'power_out',
        'C': 'open_collector',
        'E': 'open_emitter',
        'N': 'no_connect',
    }.get(pin_type, 'passive')

def _legacy_pin_shape_to_sexpr(shape):
    value = shape.upper()
    if 'X' in value:
        return 'non_logic'
    if 'F' in value:
        return 'edge_clock_high'
    if 'V' in value:
        return 'output_low'
    if 'L' in value:
        return 'clock_low' if 'C' in value else 'input_low'
    if 'C' in value and 'I' in value:
        return 'inverted_clock'
    if 'C' in value:
        return 'clock'
    if 'I' in value:
        return 'inverted'
    return 'line'

def _legacy_library_reference_prefix(reference, fallback_name):
    reference = reference.strip()
    if reference.startswith('#'):
        prefix = ''
        for ch in reference:
            if ch.isalpha() or ch in {'#', '_'}:
                prefix += ch
            else:
                break
        if len(prefix) > 1:
            return prefix
    else:
        prefix = ''
        for ch in reference:
            if ch.isalpha():
                prefix += ch
            else:
                break
        if prefix:
            return prefix
    for ch in fallback_name:
        if 'A' <= ch <= 'Z':
            return ch
    return 'U'

def _legacy_field_hidden(words, default_hidden):
    if len(words) <= 6:
        return default_hidden
    return words[6] == 'I'

def _legacy_effects_node(hidden=False, size='50'):
    value = _legacy_coord_to_mm(size)
    effects = sexpr_list(
        atom('effects'),
        sexpr_list(atom('font'), sexpr_list(atom('size'), atom(value), atom(value))),
    )
    if hidden:
        effects.children.append(atom('hide'))
    return effects

def _legacy_pin_effects_node(size):
    value = _legacy_coord_to_mm(size)
    return sexpr_list(
        atom('effects'),
        sexpr_list(atom('font'), sexpr_list(atom('size'), atom(value), atom(value))),
    )

def _legacy_text_effects_node(size, style='', bold='0'):
    value = _legacy_coord_to_mm(size)
    font = sexpr_list(atom('font'), sexpr_list(atom('size'), atom(value), atom(value)))
    if style.lower() in {'italic', 'bolditalic'}:
        font.children.append(atom('italic'))
    if _bool_value(bold, False) or style.lower() in {'bold', 'bolditalic'}:
        font.children.append(atom('bold'))
    return sexpr_list(atom('effects'), font)

def _legacy_at_node(x, y, angle='0'):
    return sexpr_list(atom('at'), atom(x), atom(y), atom(angle))

def _legacy_property_node(name, value, prop_id, hidden=False, use_id=True, x='0', y='0', angle='0', size='50'):
    node = sexpr_list(atom('property'), atom(name, True), atom(value, True), _legacy_at_node(x, y, angle))
    if use_id:
        node.children.append(sexpr_list(atom('id'), atom(prop_id)))
    node.children.append(_legacy_effects_node(hidden, size))
    return node

def _legacy_stroke_node(width):
    return sexpr_list(
        atom('stroke'),
        sexpr_list(atom('width'), atom(_legacy_coord_to_mm(width))),
        sexpr_list(atom('type'), atom('default')),
    )

def _legacy_fill_node(value):
    if value == 'F':
        fill_type = 'outline'
    elif value == 'f':
        fill_type = 'background'
    else:
        fill_type = 'none'
    return sexpr_list(atom('fill'), sexpr_list(atom('type'), atom(fill_type)))

def _legacy_draw_unit(words):
    if not words:
        return 1
    if words[0] == 'S':
        return _to_int(words[5], 1) if len(words) > 5 else 1
    if words[0] == 'P':
        return _to_int(words[2], 1) if len(words) > 2 else 1
    if words[0] == 'C':
        return _to_int(words[4], 1) if len(words) > 4 else 1
    if words[0] == 'A':
        return _to_int(words[6], 1) if len(words) > 6 else 1
    if words[0] == 'T':
        return _to_int(words[5], 1) if len(words) > 5 else 1
    return 1

def _legacy_pin_unit(words):
    return _to_int(words[9], 1) if len(words) > 9 else 1

def _legacy_append_draw_item(symbol, line):
    words = _legacy_split_words(line)
    if not words:
        return False
    if words[0] == 'S' and len(words) >= 9:
        symbol.children.append(
            sexpr_list(
                atom('rectangle'),
                sexpr_list(atom('start'), atom(_legacy_coord_to_mm(words[1])), atom(_legacy_coord_to_mm(words[2]))),
                sexpr_list(atom('end'), atom(_legacy_coord_to_mm(words[3])), atom(_legacy_coord_to_mm(words[4]))),
                _legacy_stroke_node(words[7]),
                _legacy_fill_node(words[8]),
            )
        )
        return True
    if words[0] == 'P' and len(words) >= 7 and _is_number(words[1]):
        count = _to_int(words[1], 0)
        first = 5
        if len(words) < first + count * 2:
            return False
        pts = sexpr_list(atom('pts'))
        for index in range(count):
            coord = first + index * 2
            pts.children.append(sexpr_list(atom('xy'), atom(_legacy_coord_to_mm(words[coord])), atom(_legacy_coord_to_mm(words[coord + 1]))))
        symbol.children.append(sexpr_list(atom('polyline'), pts, _legacy_stroke_node(words[4]), _legacy_fill_node(words[-1])))
        return True
    if words[0] == 'C' and len(words) >= 8:
        symbol.children.append(
            sexpr_list(
                atom('circle'),
                sexpr_list(atom('center'), atom(_legacy_coord_to_mm(words[1])), atom(_legacy_coord_to_mm(words[2]))),
                sexpr_list(atom('radius'), atom(_legacy_coord_to_mm(words[3]))),
                _legacy_stroke_node(words[6]),
                _legacy_fill_node(words[7]),
            )
        )
        return True
    if words[0] == 'A' and len(words) >= 13:
        symbol.children.append(
            sexpr_list(
                atom('arc'),
                sexpr_list(atom('start'), atom(_legacy_coord_to_mm(words[9])), atom(_legacy_coord_to_mm(words[10]))),
                sexpr_list(atom('mid'), atom(_legacy_coord_to_mm(words[1])), atom(_legacy_coord_to_mm(words[2]))),
                sexpr_list(atom('end'), atom(_legacy_coord_to_mm(words[11])), atom(_legacy_coord_to_mm(words[12]))),
                _legacy_stroke_node(words[7]),
                _legacy_fill_node(words[8]),
            )
        )
        return True
    if words[0] == 'T' and len(words) >= 8:
        text = _first_legacy_quoted_value(line) or words[7]
        tail = _legacy_split_words(line.split(_legacy_quote(text), 1)[1]) if _legacy_quote(text) in line else words[8:]
        style = tail[0] if tail else ''
        bold = tail[1] if len(tail) > 1 else '0'
        symbol.children.append(
            sexpr_list(
                atom('text'),
                atom(text, True),
                _legacy_at_node(_legacy_coord_to_mm(words[2]), _legacy_coord_to_mm(words[3]), _legacy_library_text_angle(words[1])),
                _legacy_text_effects_node(words[4], style, bold),
            )
        )
        return True
    return False

def _legacy_pin_node(words):
    if len(words) < 12:
        return None
    shape = words[12] if len(words) > 12 else ''
    node = sexpr_list(
        atom('pin'),
        atom(_legacy_pin_type_to_sexpr(words[11])),
        atom(_legacy_pin_shape_to_sexpr(shape)),
        _legacy_at_node(_legacy_coord_to_mm(words[3]), _legacy_coord_to_mm(words[4]), _legacy_pin_angle(words[6])),
        sexpr_list(atom('length'), atom(_legacy_coord_to_mm(words[5]))),
        sexpr_list(atom('name'), atom(words[1], True), _legacy_pin_effects_node(words[7] if len(words) > 7 else '50')),
        sexpr_list(atom('number'), atom(words[2], True), _legacy_pin_effects_node(words[8] if len(words) > 8 else '50')),
    )
    if 'N' in shape.upper():
        node.children.append(atom('hide'))
    return node

def _legacy_items_have_multiple_units(defn):
    if defn['unit_count'] > 1:
        return True
    for unit, _words in defn['pins']:
        if unit > 1:
            return True
    for unit, _line in defn['draw']:
        if unit > 1:
            return True
    return False

def _legacy_append_items_for_unit(symbol, defn, unit, include_common=False):
    for item_unit, line in defn['draw']:
        if item_unit == unit or (include_common and item_unit == 0):
            _legacy_append_draw_item(symbol, line)
    for item_unit, words in defn['pins']:
        if item_unit != unit and not (include_common and item_unit == 0):
            continue
        pin = _legacy_pin_node(words)
        if pin:
            symbol.children.append(pin)

def _legacy_max_unit(defn):
    max_unit = max(1, defn['unit_count'])
    for unit, _words in defn['pins']:
        max_unit = max(max_unit, unit)
    for unit, _line in defn['draw']:
        max_unit = max(max_unit, unit)
    return max_unit

def _legacy_append_unit_subsymbols(symbol, base_name, defn):
    for unit in range(_legacy_max_unit(defn) + 1):
        has_items = any(item_unit == unit for item_unit, _line in defn['draw'])
        has_items = has_items or any(item_unit == unit for item_unit, _words in defn['pins'])
        if not has_items:
            continue
        sub = sexpr_list(atom('symbol'), atom(base_name + '_' + str(unit) + '_1', True))
        _legacy_append_items_for_unit(sub, defn, unit)
        symbol.children.append(sub)

def _legacy_append_alias_unit_subsymbols(symbol, alias_base, parent_base, defn):
    for unit in range(_legacy_max_unit(defn) + 1):
        has_items = any(item_unit == unit for item_unit, _line in defn['draw'])
        has_items = has_items or any(item_unit == unit for item_unit, _words in defn['pins'])
        if not has_items:
            continue
        sub = sexpr_list(
            atom('symbol'),
            atom(alias_base + '_' + str(unit) + '_1', True),
            sexpr_list(atom('extends'), atom(parent_base + '_' + str(unit) + '_1', True)),
        )
        symbol.children.append(sub)

def _symbol_name_without_library_prefix(name):
    if ':' in name:
        suffix = name.split(':', 1)[1]
        if suffix:
            return suffix
    return name

def _legacy_parse_dcm_metadata(path):
    dcm_path = path.with_suffix('.dcm')
    if not dcm_path.exists():
        return {}
    meta = {}
    current_name = ''
    current = {}

    def flush():
        if current_name:
            meta[current_name] = dict(current)

    for line in dcm_path.read_text(encoding='utf-8-sig').splitlines():
        if line.startswith('$CMP '):
            flush()
            current_name = _sanitize_symbol_name(line[5:].strip())
            current = {}
        elif line.startswith('D '):
            current['description'] = line[2:].strip()
        elif line.startswith('K '):
            current['keywords'] = line[2:].strip()
        elif line.startswith('F '):
            current['datasheet'] = line[2:].strip()
        elif line == '$ENDCMP':
            flush()
            current_name = ''
            current = {}
    flush()
    return meta

def _legacy_library_to_sexpr_text(doc, target_version):
    use_ids = (not _is_number(target_version)) or int(target_version) < 20220914
    root = sexpr_list(atom('kicad_symbol_lib'), sexpr_list(atom('version'), atom(target_version)), sexpr_list(atom('generator'), atom('kicad-backport')))
    doc_meta = _legacy_parse_dcm_metadata(doc.path)
    lines = doc.raw_text.splitlines()
    converted = converted_pins = converted_draw = converted_aliases = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.startswith('DEF '):
            i += 1
            continue
        words = _legacy_split_words(line)
        if len(words) < 2:
            i += 1
            continue
        name = _sanitize_symbol_name(words[1])
        value = name
        reference = _legacy_library_reference_prefix(words[2] if len(words) > 2 else '', name)
        show_pin_numbers = words[5] != 'N' if len(words) > 5 else True
        show_pin_names = words[6] != 'N' if len(words) > 6 else True
        defn = {'unit_count': _to_int(words[7], 1) if len(words) > 7 else 1, 'pins': [], 'draw': []}
        fields = {
            'Reference': {'value': reference, 'x': '0', 'y': '0', 'angle': '0', 'hidden': False},
            'Value': {'value': value, 'x': '0', 'y': '0', 'angle': '0', 'hidden': False},
            'Footprint': {'value': '', 'x': '0', 'y': '0', 'angle': '0', 'hidden': True},
            'Datasheet': {'value': '', 'x': '0', 'y': '0', 'angle': '0', 'hidden': True},
        }
        extra_fields = []
        aliases = []
        i += 1
        while i < len(lines):
            item = lines[i]
            i += 1
            if item == 'ENDDEF':
                break
            item_words = _legacy_split_words(item)
            if not item_words:
                continue
            tag = item_words[0]
            if tag in {'F0', 'F1', 'F2', 'F3'}:
                field_name = {'F0': 'Reference', 'F1': 'Value', 'F2': 'Footprint', 'F3': 'Datasheet'}[tag]
                parsed = _first_legacy_quoted_value(item)
                if tag == 'F0':
                    parsed = _legacy_library_reference_prefix(parsed, name)
                elif tag == 'F1' and not parsed:
                    parsed = value
                fields[field_name]['value'] = parsed
                if len(item_words) >= 6:
                    fields[field_name]['x'] = _legacy_coord_to_mm(item_words[2])
                    fields[field_name]['y'] = _legacy_coord_to_mm(item_words[3])
                    fields[field_name]['angle'] = _legacy_field_angle(item_words[5])
                    fields[field_name]['hidden'] = _legacy_field_hidden(item_words, fields[field_name]['hidden'])
                if tag == 'F0':
                    reference = parsed
                elif tag == 'F1':
                    value = parsed
            elif len(tag) > 1 and tag[0] == 'F' and tag[1:].isdigit():
                values = _legacy_quoted_values(item)
                prop_id = tag[1:]
                field = {
                    'name': values[-1] if len(values) > 1 and values[-1] else 'Field' + prop_id,
                    'value': values[0] if values else '',
                    'id': prop_id,
                    'x': '0',
                    'y': '0',
                    'angle': '0',
                    'hidden': False,
                }
                if len(item_words) >= 6:
                    field['x'] = _legacy_coord_to_mm(item_words[2])
                    field['y'] = _legacy_coord_to_mm(item_words[3])
                    field['angle'] = _legacy_field_angle(item_words[5])
                    field['hidden'] = _legacy_field_hidden(item_words, field['hidden'])
                extra_fields.append(field)
            elif tag == 'X':
                defn['pins'].append((_legacy_pin_unit(item_words), item_words))
                converted_pins += 1
            elif tag == 'ALIAS':
                for alias_name in item_words[1:]:
                    alias_name = _sanitize_symbol_name(alias_name)
                    if alias_name:
                        aliases.append(alias_name)
            elif tag in {'S', 'P', 'C', 'A', 'T'}:
                defn['draw'].append((_legacy_draw_unit(item_words), item))
                converted_draw += 1
        symbol = sexpr_list(atom('symbol'), atom(name, True))
        if not show_pin_numbers:
            symbol.children.append(sexpr_list(atom('pin_numbers'), atom('hide')))
        if not show_pin_names:
            symbol.children.append(sexpr_list(atom('pin_names'), atom('hide')))
        symbol.children.append(sexpr_list(atom('in_bom'), atom('yes')))
        symbol.children.append(sexpr_list(atom('on_board'), atom('yes')))
        meta = doc_meta.get(name, {})
        if meta.get('datasheet'):
            fields['Datasheet']['value'] = meta['datasheet']
        for prop_id, prop_name in enumerate(['Reference', 'Value', 'Footprint', 'Datasheet']):
            field = fields[prop_name]
            symbol.children.append(_legacy_property_node(prop_name, field['value'], str(prop_id), field['hidden'], use_ids, field['x'], field['y'], field['angle']))
        for field in extra_fields:
            symbol.children.append(_legacy_property_node(field['name'], field['value'], field['id'], field['hidden'], use_ids, field['x'], field['y'], field['angle']))
        if meta.get('description'):
            symbol.children.append(_legacy_property_node('ki_description', meta['description'], '4', False, use_ids))
        if meta.get('keywords'):
            symbol.children.append(_legacy_property_node('ki_keywords', meta['keywords'], '5', False, use_ids))
        unit_base = _symbol_name_without_library_prefix(name)
        if _legacy_items_have_multiple_units(defn):
            _legacy_append_unit_subsymbols(symbol, unit_base, defn)
        else:
            _legacy_append_items_for_unit(symbol, defn, 1, True)
        root.children.append(symbol)
        for alias_name in aliases:
            if not alias_name or alias_name == name:
                continue
            alias_symbol = sexpr_list(atom('symbol'), atom(alias_name, True), sexpr_list(atom('extends'), atom(name, True)))
            if _legacy_items_have_multiple_units(defn):
                _legacy_append_alias_unit_subsymbols(alias_symbol, _symbol_name_without_library_prefix(alias_name), unit_base, defn)
            root.children.append(alias_symbol)
            converted_aliases += 1
        converted += 1
    warnings = []
    if converted == 0:
        warnings.append('converted legacy symbol library header only; no DEF records were found')
    else:
        warnings.append('converted legacy symbol DEF records; drawing primitives and pins are not yet fully mapped')
    if converted_pins:
        warnings.append('converted legacy symbol pin records')
    if converted_draw:
        warnings.append('converted legacy symbol drawing primitives')
    if converted_aliases:
        warnings.append('converted legacy symbol aliases')
    if doc_meta:
        warnings.append('merged paired legacy .dcm documentation metadata into symbol properties')
    if _is_number(target_version) and int(target_version) >= 20240108:
        _warn_if_changed(warnings, expand_font_style_atoms(root), 'upgraded symbol library font style atoms to boolean lists')
    return (format_sexpr(root), warnings)

def _legacy_documentation_to_sexpr_text(doc, target_version):
    use_ids = (not _is_number(target_version)) or int(target_version) < 20220914
    root = sexpr_list(atom('kicad_symbol_lib'), sexpr_list(atom('version'), atom(target_version)), sexpr_list(atom('generator'), atom('kicad-backport')))
    metadata = {}
    current_name = ''
    current = {}

    def flush():
        if current_name:
            metadata[current_name] = dict(current)

    for line in doc.raw_text.splitlines():
        if line.startswith('$CMP '):
            flush()
            current_name = _sanitize_symbol_name(line[5:].strip())
            current = {}
        elif line.startswith('D '):
            current['description'] = line[2:].strip()
        elif line.startswith('K '):
            current['keywords'] = line[2:].strip()
        elif line.startswith('F '):
            current['datasheet'] = line[2:].strip()
        elif line == '$ENDCMP':
            flush()
            current_name = ''
            current = {}
    flush()
    for name, meta in metadata.items():
        symbol = sexpr_list(atom('symbol'), atom(name, True))
        symbol.children.append(sexpr_list(atom('in_bom'), atom('yes')))
        symbol.children.append(sexpr_list(atom('on_board'), atom('yes')))
        symbol.children.append(_legacy_property_node('Reference', _library_reference_prefix(name), '0', False, use_ids))
        symbol.children.append(_legacy_property_node('Value', name, '1', False, use_ids))
        symbol.children.append(_legacy_property_node('Footprint', '', '2', True, use_ids))
        symbol.children.append(_legacy_property_node('Datasheet', meta.get('datasheet', ''), '3', True, use_ids))
        if meta.get('description'):
            symbol.children.append(_legacy_property_node('ki_description', meta['description'], '4', False, use_ids))
        if meta.get('keywords'):
            symbol.children.append(_legacy_property_node('ki_keywords', meta['keywords'], '5', False, use_ids))
        root.children.append(symbol)
    warnings = ['converted legacy documentation file to an empty symbol library' if not metadata else 'converted legacy documentation metadata to symbol properties']
    return (format_sexpr(root), warnings)

def _deterministic_uuid(seed):
    digest = hashlib.sha1(seed.encode('utf-8')).hexdigest()
    return '{}-{}-{}-{}-{}'.format(digest[:8], digest[8:12], digest[12:16], digest[16:20], digest[20:32])

def _legacy_uuid_from_tstamp(value):
    return _deterministic_uuid('legacy-tstamp:' + value)

def _legacy_instance_path_from_ar_path(path):
    if not path or not path.startswith('/'):
        return path
    parts = [part for part in path.split('/') if part]
    if not parts:
        return '/'
    return ''.join('/' + _legacy_uuid_from_tstamp(part) for part in parts)

def _legacy_unquote(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        value = value[1:-1]
    out = []
    escaped = False
    for ch in value:
        if escaped:
            if ch == 'n':
                out.append('\n')
            elif ch == 't':
                out.append('\t')
            elif ch != 'r':
                out.append(ch)
            escaped = False
        elif ch == '\\':
            escaped = True
        else:
            out.append(ch)
    return ''.join(out)

def _legacy_schematic_meta(text):
    meta = {'paper': 'A4', 'title': '', 'date': '', 'rev': '', 'company': '', 'comments': [''] * 9}
    for line in text.splitlines():
        words = _legacy_split_words(line)
        if not words:
            continue
        if words[0] == '$Descr' and len(words) > 1:
            meta['paper'] = words[1]
        elif line.startswith('Title '):
            meta['title'] = _legacy_unquote(line[6:])
        elif line.startswith('Date '):
            meta['date'] = _legacy_unquote(line[5:])
        elif line.startswith('Rev '):
            meta['rev'] = _legacy_unquote(line[4:])
        elif line.startswith('Comp '):
            meta['company'] = _legacy_unquote(line[5:])
        elif line.startswith('Comment') and len(words) > 1:
            number = words[0][7:]
            if number.isdigit():
                index = int(number)
                if 1 <= index <= 9:
                    meta['comments'][index - 1] = _legacy_unquote(line[len(words[0]) + 1:])
    return meta

def _legacy_title_block_node(meta):
    title = sexpr_list(atom('title_block'))
    if meta['title']:
        title.children.append(sexpr_list(atom('title'), atom(meta['title'], True)))
    if meta['date']:
        title.children.append(sexpr_list(atom('date'), atom(meta['date'], True)))
    if meta['rev']:
        title.children.append(sexpr_list(atom('rev'), atom(meta['rev'], True)))
    if meta['company']:
        title.children.append(sexpr_list(atom('company'), atom(meta['company'], True)))
    for index, comment in enumerate(meta['comments'], 1):
        if comment:
            title.children.append(sexpr_list(atom('comment'), atom(str(index)), atom(comment, True)))
    return title

def _legacy_schematic_field_hidden(words, default_hidden):
    if len(words) <= 7:
        return default_hidden
    return words[7] != '0000'

def _legacy_sheet_pin_type_to_sexpr(value):
    lower = value.lower()
    if lower in {'i', 'input'}:
        return 'input'
    if lower in {'o', 'output'}:
        return 'output'
    if lower in {'b', 'bidi', 'bidirectional'}:
        return 'bidirectional'
    if lower in {'t', 'tristate', 'tri_state'}:
        return 'tri_state'
    return 'passive'

def _legacy_label_shape_to_sexpr(value):
    lower = value.lower()
    if lower == 'input':
        return 'input'
    if lower == 'output':
        return 'output'
    if lower in {'bidi', 'bidirectional'}:
        return 'bidirectional'
    if lower in {'tristate', 'tri_state'}:
        return 'tri_state'
    return 'passive'

def _legacy_schematic_at_item_node(head, x, y, seed):
    return sexpr_list(
        atom(head),
        sexpr_list(atom('at'), atom(_legacy_coord_to_mm(x)), atom(_legacy_coord_to_mm(y))),
        sexpr_list(atom('uuid'), atom(_deterministic_uuid(seed))),
    )

def _legacy_schematic_line_node(head, words, seed):
    if len(words) < 4:
        return None
    return sexpr_list(
        atom(head),
        sexpr_list(
            atom('pts'),
            sexpr_list(atom('xy'), atom(_legacy_coord_to_mm(words[0])), atom(_legacy_coord_to_mm(words[1]))),
            sexpr_list(atom('xy'), atom(_legacy_coord_to_mm(words[2])), atom(_legacy_coord_to_mm(words[3]))),
        ),
        sexpr_list(atom('uuid'), atom(_deterministic_uuid(seed))),
    )

def _legacy_schematic_polyline_node(words, seed):
    node = _legacy_schematic_line_node('polyline', words, seed)
    if node:
        node.children.insert(
            2,
            sexpr_list(
                atom('stroke'),
                sexpr_list(atom('width'), atom('0.1524')),
                sexpr_list(atom('type'), atom('default')),
            ),
        )
    return node

def _legacy_schematic_bus_entry_node(words, seed):
    if len(words) < 4:
        return None
    x1 = _to_int(words[0], 0)
    y1 = _to_int(words[1], 0)
    x2 = _to_int(words[2], x1)
    y2 = _to_int(words[3], y1)
    return sexpr_list(
        atom('bus_entry'),
        sexpr_list(atom('at'), atom(_legacy_coord_to_mm(words[0])), atom(_legacy_coord_to_mm(words[1]))),
        sexpr_list(atom('size'), atom(_legacy_coord_to_mm(str(x2 - x1))), atom(_legacy_coord_to_mm(str(y2 - y1)))),
        sexpr_list(atom('uuid'), atom(_deterministic_uuid(seed))),
    )

def _legacy_schematic_label_node(head, text, x, y, orientation, shape, size, seed):
    node = sexpr_list(atom(head), atom(text, True))
    if head in {'global_label', 'hierarchical_label'}:
        node.children.append(sexpr_list(atom('shape'), atom(_legacy_label_shape_to_sexpr(shape))))
    node.children.append(_legacy_at_node(_legacy_coord_to_mm(x), _legacy_coord_to_mm(y), _legacy_text_angle(orientation)))
    node.children.append(_legacy_pin_effects_node(size))
    node.children.append(sexpr_list(atom('uuid'), atom(_deterministic_uuid(seed))))
    return node

def _legacy_transform_from_matrix(words):
    if len(words) != 4:
        return ('0', '')
    try:
        matrix = tuple(int(part) for part in words)
    except ValueError:
        return ('0', '')
    mapping = {
        (0, -1, -1, 0): ('90', ''),
        (-1, 0, 0, 1): ('180', ''),
        (0, 1, 1, 0): ('270', ''),
        (1, 0, 0, 1): ('0', 'x'),
        (0, -1, 1, 0): ('90', 'x'),
        (-1, 0, 0, -1): ('180', 'x'),
        (0, 1, -1, 0): ('270', 'x'),
    }
    return mapping.get(matrix, ('0', ''))

def _legacy_quoted_attribute(line, key):
    needle = key + '="'
    pos = line.find(needle)
    if pos < 0:
        return ''
    pos += len(needle)
    out = []
    escaped = False
    while pos < len(line):
        ch = line[pos]
        pos += 1
        if escaped:
            out.append(ch)
            escaped = False
        elif ch == '\\':
            escaped = True
        elif ch == '"':
            break
        else:
            out.append(ch)
    return ''.join(out)

def _legacy_is_unannotated_reference(value):
    return not value or '?' in value

def _legacy_normalize_hidden_reference(reference, value, symbol_def=None):
    if len(reference) < 3 or not reference.startswith('#U'):
        return reference
    suffix_start = 2
    while suffix_start < len(reference) and not reference[suffix_start].isdigit():
        suffix_start += 1
    suffix = reference[suffix_start:] if suffix_start < len(reference) else ''
    symbol_reference = symbol_def.get('reference', '') if symbol_def else ''
    if len(symbol_reference) >= 2 and symbol_reference.startswith('#'):
        return symbol_reference + suffix
    if value == 'PWR_FLAG':
        return '#FLG' + suffix
    if value and (value[0] in {'+', '-'} or value in {'GND', 'VCC', 'VDD', 'VSS'}):
        return '#PWR' + suffix
    return reference

def _legacy_schematic_field_state():
    return {'x': '0', 'y': '0', 'angle': '0', 'size': '50'}

def _legacy_schematic_library_names(path, lines):
    names = []
    for line in lines:
        if line.startswith('LIBS:'):
            name = line[5:].strip()
            if name and name not in names:
                names.append(name)
    fallback = path.stem + '-cache'
    if fallback not in names:
        names.append(fallback)
    return names

def _cache_name_for_legacy_lib_id(lib_id):
    return lib_id.replace(':', '_')

def _legacy_schematic_cache_maps(path, lines):
    defs = {}
    libraries = {}
    for library_name in _legacy_schematic_library_names(path, lines):
        lib_path = path.parent / (library_name + '.lib')
        if not lib_path.exists():
            continue
        current_name = ''
        current = {'pins': [], 'reference': ''}
        aliases = []

        def flush():
            nonlocal current_name, current, aliases
            if not current_name:
                return
            for name in [current_name] + aliases:
                defs[name] = {'pins': list(current['pins']), 'reference': current.get('reference', '')}
                libraries[name] = library_name
            current_name = ''
            current = {'pins': [], 'reference': ''}
            aliases = []

        for line in lib_path.read_text(encoding='utf-8-sig').splitlines():
            words = _legacy_split_words(line)
            if not words:
                continue
            if words[0] == 'DEF' and len(words) > 1:
                flush()
                current_name = words[1]
                current['reference'] = _legacy_library_reference_prefix(words[2] if len(words) > 2 else '', current_name)
            elif words[0] == 'ALIAS':
                aliases.extend(words[1:])
            elif words[0] == 'X':
                current['pins'].append(words)
            elif words[0] == 'ENDDEF':
                flush()
        flush()
    return defs, libraries

def _append_legacy_schematic_symbol_pin_nodes(symbol, symbol_def, seed):
    if not symbol_def:
        return 0
    added = 0
    seen = set()
    for words in symbol_def.get('pins', []):
        if len(words) < 3:
            continue
        number = words[2]
        if not number or number in seen:
            continue
        seen.add(number)
        symbol.children.append(
            sexpr_list(
                atom('pin'),
                atom(number, True),
                sexpr_list(atom('uuid'), atom(_deterministic_uuid(seed + ':pin:' + number))),
            )
        )
        added += 1
    return added

def _legacy_schematic_to_sexpr_text(doc, target_version):
    use_ids = (not _is_number(target_version)) or int(target_version) < 20230121
    target_int = int(target_version) if _is_number(target_version) else 0
    include_pin_uuid_blocks = bool(target_int and target_int <= 20211123)
    meta = _legacy_schematic_meta(doc.raw_text)
    root = sexpr_list(
        atom('kicad_sch'),
        sexpr_list(atom('version'), atom(target_version)),
        sexpr_list(atom('generator'), atom('kicad-backport')),
        sexpr_list(atom('uuid'), atom(_deterministic_uuid(str(doc.path) + ':schematic-root'))),
        sexpr_list(atom('paper'), atom(meta['paper'], True)),
    )
    title = _legacy_title_block_node(meta)
    if len(title.children) > 1:
        root.children.append(title)
    sheet_instances = sexpr_list(atom('sheet_instances'), sexpr_list(atom('path'), atom('/', True), sexpr_list(atom('page'), atom('1', True))))
    symbol_instances = sexpr_list(atom('symbol_instances'))
    counts = {
        'symbols': 0,
        'wires': 0,
        'sheets': 0,
        'labels': 0,
        'junctions': 0,
        'no_connects': 0,
        'buses': 0,
        'bus_entries': 0,
        'sheet_pins': 0,
        'drawings': 0,
    }
    lines = doc.raw_text.splitlines()
    cache_defs, cache_libraries = _legacy_schematic_cache_maps(doc.path, lines)
    next_sheet_page = 2
    i = 0
    while i < len(lines):
        line = lines[i]
        if line == '$Sheet':
            block = []
            x = y = '0'
            w = '20.32'
            h = '12.7'
            tstamp = ''
            sheet_name = 'Sheet'
            sheet_file = ''
            sheet_name_size = '50'
            sheet_file_size = '50'
            sheet_pins = []
            i += 1
            while i < len(lines):
                item = lines[i]
                block.append(item)
                i += 1
                if item == '$EndSheet':
                    break
                words = _legacy_split_words(item)
                if not words:
                    continue
                if words[0] == 'S' and len(words) > 4:
                    x = _legacy_coord_to_mm(words[1])
                    y = _legacy_coord_to_mm(words[2])
                    w = _legacy_coord_to_mm(words[3])
                    h = _legacy_coord_to_mm(words[4])
                elif words[0] == 'U' and len(words) > 1:
                    tstamp = words[1]
                elif words[0] == 'F0':
                    sheet_name = _first_legacy_quoted_value(item)
                    if len(words) > 2:
                        sheet_name_size = words[2]
                elif words[0] == 'F1':
                    sheet_file = _replace_trailing_extension(_first_legacy_quoted_value(item), '.sch', '.kicad_sch')
                    if len(words) > 2:
                        sheet_file_size = words[2]
                elif len(words[0]) > 1 and words[0][0] == 'F' and words[0][1:].isdigit() and int(words[0][1:]) >= 2:
                    pin_name = _first_legacy_quoted_value(item)
                    if len(words) >= 6:
                        pin_size = words[6] if len(words) > 6 else '50'
                        pin = sexpr_list(
                            atom('pin'),
                            atom(pin_name, True),
                            sexpr_list(atom('type'), atom(_legacy_sheet_pin_type_to_sexpr(words[2]))),
                            _legacy_at_node(_legacy_coord_to_mm(words[4]), _legacy_coord_to_mm(words[5]), _legacy_pin_angle(words[3])),
                            _legacy_effects_node(False, pin_size),
                            sexpr_list(atom('uuid'), atom(_deterministic_uuid(str(doc.path) + ':sheet-pin:' + item))),
                        )
                        sheet_pins.append(pin)
                        counts['sheet_pins'] += 1
            uuid = _legacy_uuid_from_tstamp(tstamp) if tstamp else _deterministic_uuid(str(doc.path) + ':sheet:' + '\n'.join(block))
            sheet = sexpr_list(
                atom('sheet'),
                sexpr_list(atom('at'), atom(x), atom(y)),
                sexpr_list(atom('size'), atom(w), atom(h)),
                sexpr_list(atom('uuid'), atom(uuid)),
                _legacy_property_node('Sheet name', sheet_name, '0', False, use_ids, x, y, '0', sheet_name_size),
                _legacy_property_node('Sheet file', sheet_file, '1', False, use_ids, x, y, '0', sheet_file_size),
            )
            sheet.children.extend(sheet_pins)
            root.children.append(sheet)
            sheet_instances.children.append(sexpr_list(atom('path'), atom('/' + uuid, True), sexpr_list(atom('page'), atom(str(next_sheet_page), True))))
            next_sheet_page += 1
            counts['sheets'] += 1
            continue
        if line == '$Comp':
            block = []
            lib_id = ''
            reference = ''
            unit = '1'
            value = ''
            footprint = ''
            datasheet = ''
            x = y = '0'
            tstamp = ''
            transform_angle = '0'
            transform_mirror = ''
            reference_hidden = False
            value_hidden = False
            footprint_hidden = True
            datasheet_hidden = True
            reference_field = _legacy_schematic_field_state()
            value_field = _legacy_schematic_field_state()
            footprint_field = _legacy_schematic_field_state()
            datasheet_field = _legacy_schematic_field_state()
            custom_fields = []
            ar_instances = []
            i += 1
            while i < len(lines):
                item = lines[i]
                block.append(item)
                i += 1
                if item == '$EndComp':
                    break
                words = _legacy_split_words(item)
                if not words:
                    continue
                if words[0] == 'L' and len(words) > 2:
                    lib_id = words[1]
                    reference = words[2]
                elif words[0] == 'U' and len(words) > 1:
                    unit = words[1]
                    if len(words) > 3:
                        tstamp = words[3]
                elif words[0] == 'P' and len(words) > 2:
                    x = _legacy_coord_to_mm(words[1])
                    y = _legacy_coord_to_mm(words[2])
                elif words[0] == 'F' and len(words) > 2:
                    field_value = _first_legacy_quoted_value(item)
                    state = _legacy_schematic_field_state()
                    if len(words) >= 6:
                        state['angle'] = _legacy_field_angle(words[3])
                        state['x'] = _legacy_coord_to_mm(words[4])
                        state['y'] = _legacy_coord_to_mm(words[5])
                    if len(words) >= 7:
                        state['size'] = words[6]
                    if words[1] == '0':
                        if field_value and (_legacy_is_unannotated_reference(reference) or not _legacy_is_unannotated_reference(field_value)):
                            reference = field_value
                        reference_field = state
                        reference_hidden = _legacy_schematic_field_hidden(words, False)
                    elif words[1] == '1':
                        value = field_value
                        value_field = state
                        value_hidden = _legacy_schematic_field_hidden(words, False)
                    elif words[1] == '2':
                        footprint = field_value
                        footprint_field = state
                        footprint_hidden = _legacy_schematic_field_hidden(words, True)
                    elif words[1] == '3':
                        datasheet = field_value
                        datasheet_field = state
                        datasheet_hidden = _legacy_schematic_field_hidden(words, True)
                    elif words[1].isdigit() and int(words[1]) >= 4:
                        values = _legacy_quoted_values(item)
                        field_name = values[-1] if len(values) > 1 and values[-1] else 'Field' + words[1]
                        custom_fields.append({
                            'name': field_name,
                            'value': values[0] if values else field_value,
                            'id': words[1],
                            'hidden': _legacy_schematic_field_hidden(words, False),
                            'state': state,
                        })
                elif words[0] == 'AR':
                    ar_path = _legacy_quoted_attribute(item, 'Path')
                    if ar_path:
                        ar_instances.append({
                            'path': ar_path,
                            'reference': _legacy_quoted_attribute(item, 'Ref'),
                            'part': _legacy_quoted_attribute(item, 'Part'),
                        })
                elif len(words) == 4:
                    transform_angle, transform_mirror = _legacy_transform_from_matrix(words)
            if not lib_id:
                continue
            if not value:
                value = lib_id
            cache_name = _cache_name_for_legacy_lib_id(lib_id)
            symbol_def = cache_defs.get(cache_name)
            explicit_library = ':' in lib_id
            output_lib_id = lib_id if explicit_library or cache_name not in cache_libraries else cache_libraries[cache_name] + ':' + cache_name
            if _legacy_is_unannotated_reference(reference):
                for ar in ar_instances:
                    if ar['reference'] and not _legacy_is_unannotated_reference(ar['reference']):
                        reference = ar['reference']
                        break
            reference = _legacy_normalize_hidden_reference(reference, value, symbol_def)
            uuid = _legacy_uuid_from_tstamp(tstamp) if tstamp else _deterministic_uuid(str(doc.path) + ':comp:' + '\n'.join(block))
            symbol = sexpr_list(
                atom('symbol'),
                sexpr_list(atom('lib_id'), atom(output_lib_id, True)),
                _legacy_at_node(x, y, transform_angle),
            )
            if transform_mirror:
                symbol.children.append(sexpr_list(atom('mirror'), atom(transform_mirror)))
            symbol.children.extend([
                sexpr_list(atom('unit'), atom(unit)),
                sexpr_list(atom('in_bom'), atom('yes')),
                sexpr_list(atom('on_board'), atom('yes')),
                sexpr_list(atom('uuid'), atom(uuid)),
                _legacy_property_node('Reference', reference, '0', reference_hidden, use_ids, reference_field['x'], reference_field['y'], reference_field['angle'], reference_field['size']),
                _legacy_property_node('Value', value, '1', value_hidden, use_ids, value_field['x'], value_field['y'], value_field['angle'], value_field['size']),
                _legacy_property_node('Footprint', footprint, '2', footprint_hidden, use_ids, footprint_field['x'], footprint_field['y'], footprint_field['angle'], footprint_field['size']),
                _legacy_property_node('Datasheet', datasheet, '3', datasheet_hidden, use_ids, datasheet_field['x'], datasheet_field['y'], datasheet_field['angle'], datasheet_field['size']),
            ])
            for field in custom_fields:
                state = field['state']
                symbol.children.append(_legacy_property_node(field['name'], field['value'], field['id'], field['hidden'], use_ids, state['x'], state['y'], state['angle'], state['size']))
            if include_pin_uuid_blocks:
                _append_legacy_schematic_symbol_pin_nodes(symbol, symbol_def, str(doc.path) + ':comp:' + '\n'.join(block))
            root.children.append(symbol)
            instance = sexpr_list(
                atom('path'),
                atom('/' + uuid, True),
                sexpr_list(atom('reference'), atom(reference, True)),
                sexpr_list(atom('unit'), atom(unit)),
                sexpr_list(atom('value'), atom(value, True)),
                sexpr_list(atom('footprint'), atom(footprint, True)),
            )
            symbol_instances.children.append(instance)
            for ar in ar_instances:
                ar_path = _legacy_instance_path_from_ar_path(ar['path'])
                if not ar_path:
                    continue
                symbol_instances.children.append(
                    sexpr_list(
                        atom('path'),
                        atom(ar_path, True),
                        sexpr_list(atom('reference'), atom(ar['reference'] or reference, True)),
                        sexpr_list(atom('unit'), atom(ar['part'] or unit)),
                        sexpr_list(atom('value'), atom(value, True)),
                        sexpr_list(atom('footprint'), atom(footprint, True)),
                    )
                )
            counts['symbols'] += 1
            continue
        if line in {'Wire Wire Line', 'Wire Bus Line'} and i + 1 < len(lines):
            i += 1
            words = _legacy_split_words(lines[i])
            head = 'bus' if line == 'Wire Bus Line' else 'wire'
            node = _legacy_schematic_line_node(head, words, str(doc.path) + ':' + head + ':' + lines[i])
            if node:
                root.children.append(node)
                counts['buses' if head == 'bus' else 'wires'] += 1
        elif line == 'Wire Notes Line' and i + 1 < len(lines):
            i += 1
            node = _legacy_schematic_polyline_node(_legacy_split_words(lines[i]), str(doc.path) + ':notes-line:' + lines[i])
            if node:
                root.children.append(node)
                counts['drawings'] += 1
        elif line.startswith('Entry ') and i + 1 < len(lines):
            i += 1
            node = _legacy_schematic_bus_entry_node(_legacy_split_words(lines[i]), str(doc.path) + ':entry:' + line + ':' + lines[i])
            if node:
                root.children.append(node)
                counts['bus_entries'] += 1
        elif line.startswith('Connection '):
            words = _legacy_split_words(line)
            if len(words) > 3:
                root.children.append(_legacy_schematic_at_item_node('junction', words[2], words[3], str(doc.path) + ':junction:' + line))
                counts['junctions'] += 1
        elif line.startswith('NoConn '):
            words = _legacy_split_words(line)
            if len(words) > 3:
                root.children.append(_legacy_schematic_at_item_node('no_connect', words[2], words[3], str(doc.path) + ':noconnect:' + line))
                counts['no_connects'] += 1
        elif line.startswith('Text ') and i + 1 < len(lines):
            words = _legacy_split_words(line)
            if len(words) >= 6:
                i += 1
                text = lines[i]
                head = ''
                shape = ''
                size = words[5]
                if words[1] == 'Label':
                    head = 'label'
                elif words[1] == 'GLabel':
                    head = 'global_label'
                    shape = words[6] if len(words) > 6 else 'UnSpc'
                elif words[1] == 'HLabel':
                    head = 'hierarchical_label'
                    shape = words[6] if len(words) > 6 else 'UnSpc'
                elif words[1] == 'Notes':
                    head = 'text'
                if head:
                    root.children.append(_legacy_schematic_label_node(head, text, words[2], words[3], words[4], shape, size, str(doc.path) + ':text:' + line + ':' + text))
                    counts['labels'] += 1
        i += 1
    root.children.append(sheet_instances)
    root.children.append(symbol_instances)
    warnings = []
    if counts['symbols']:
        warnings.append('converted legacy schematic component records to symbol instances')
    if counts['wires']:
        warnings.append('converted legacy schematic wire line records')
    if counts['sheets']:
        warnings.append('converted legacy schematic sheet records')
    if counts['labels']:
        warnings.append('converted legacy schematic text/label records')
    if counts['junctions']:
        warnings.append('converted legacy schematic junction records')
    if counts['no_connects']:
        warnings.append('converted legacy schematic no-connect records')
    if counts['buses']:
        warnings.append('converted legacy schematic bus records')
    if counts['bus_entries']:
        warnings.append('converted legacy schematic bus-entry records')
    if counts['sheet_pins']:
        warnings.append('converted legacy schematic sheet pin records')
    if counts['drawings']:
        warnings.append('converted legacy schematic notes line records')
    warnings.append('converted legacy schematic metadata; non-wire drawing items are not yet fully mapped')
    return (format_sexpr(root), warnings)

LEGACY_PROJECT_SETTING_ORDER = [
    'update',
    'version',
    'last_client',
    'LibDir',
    'NetIExt',
    'CmpExt',
    'PageLayoutDescrFile',
    'PlotDirectoryName',
    'SubpartIdSeparator',
    'SubpartFirstId',
]

LEGACY_PROJECT_SETTING_DEFAULTS = {
    'update': '0',
    'version': '1',
    'last_client': 'kicad-backport',
    'LibDir': '',
    'NetIExt': 'net',
    'CmpExt': '.cmp',
    'PageLayoutDescrFile': '',
    'PlotDirectoryName': '',
    'SubpartIdSeparator': '0',
    'SubpartFirstId': '65',
}

def _parse_legacy_project_meta(text):
    settings = {}
    libraries = []
    for line in text.splitlines():
        trimmed = line.strip()
        if not trimmed or trimmed.startswith('#') or trimmed.startswith('['):
            continue
        if '=' not in trimmed:
            continue
        key, value = trimmed.split('=', 1)
        key = key.strip()
        value = value.strip()
        if key.startswith('LibName'):
            if value:
                libraries.append(value)
            continue
        if key in LEGACY_PROJECT_SETTING_ORDER:
            settings[key] = value
    return {'settings': settings, 'libraries': libraries}

def _legacy_project_to_json_text(doc):
    meta = _parse_legacy_project_meta(doc.raw_text)
    project_name = doc.path.stem
    data = {
        'board': {},
        'libraries': {
            'legacy_symbol_libraries': meta['libraries'],
        },
        'legacy': {
            'project_settings': {},
        },
        'meta': {
            'filename': project_name + '.kicad_pro',
            'version': 1,
        },
        'net_settings': {},
        'schematic': {},
    }
    for key in LEGACY_PROJECT_SETTING_ORDER:
        if key in meta['settings']:
            data['legacy']['project_settings'][key] = meta['settings'][key]
    warnings = ['converted legacy project to minimal KiCad 6+ project JSON']
    if meta['settings']:
        warnings.append('preserved legacy project settings in JSON legacy.project_settings')
    if meta['libraries']:
        warnings.append('preserved legacy project symbol library names')
    return (json.dumps(data, ensure_ascii=False, indent=2) + '\n', warnings)

def _project_json_data(text):
    try:
        parsed = json.loads(text) if text.strip() else {}
    except Exception:
        parsed = {}
    return parsed if isinstance(parsed, dict) else {}

def _symbol_library_nicknames_from_table(project_dir):
    table = project_dir / 'sym-lib-table'
    if not table.exists():
        return []
    try:
        root = parse_sexpr(table.read_text(encoding='utf-8-sig'))
    except Exception:
        return []
    names = []
    for child in root.children:
        if child.atom is not None or child.head() != 'lib':
            continue
        name = _child_atom_or_empty(child, 'name')
        if name and name not in names:
            names.append(name)
    return names

def _local_symbol_library_stems(project_dir):
    if not project_dir.exists():
        return []
    names = []
    for path in sorted(project_dir.glob('*.kicad_sym')):
        if path.stem and path.stem not in names:
            names.append(path.stem)
    return names

def _project_json_to_legacy_text(doc):
    data = _project_json_data(doc.raw_text)
    settings = {}
    legacy = data.get('legacy', {})
    if isinstance(legacy, dict):
        raw_settings = legacy.get('project_settings', {})
        if isinstance(raw_settings, dict):
            for key in LEGACY_PROJECT_SETTING_ORDER:
                if key in raw_settings:
                    settings[key] = str(raw_settings[key])
    libraries = []
    raw_libraries = data.get('libraries', {})
    if isinstance(raw_libraries, dict):
        values = raw_libraries.get('legacy_symbol_libraries', [])
        if isinstance(values, list):
            for value in values:
                text = str(value)
                if text and text not in libraries:
                    libraries.append(text)
    if not libraries:
        libraries = _symbol_library_nicknames_from_table(doc.path.parent)
    if not libraries:
        libraries = _local_symbol_library_stems(doc.path.parent)
    lines = []
    for key in LEGACY_PROJECT_SETTING_ORDER:
        value = settings.get(key, LEGACY_PROJECT_SETTING_DEFAULTS[key])
        lines.append(key + '=' + value)
    for index, library in enumerate(libraries, 1):
        lines.append('LibName{}={}'.format(index, library))
    warnings = ['converted project JSON to minimal legacy .pro settings']
    if settings:
        warnings.append('restored legacy project settings from JSON')
    if libraries:
        warnings.append('restored legacy project library names')
    return ('\n'.join(lines) + '\n', warnings)

def convert_legacy_to_sexpr_text(doc, target_version, target_kind):
    if target_kind == 'schematic':
        return _legacy_schematic_to_sexpr_text(doc, target_version)
    elif target_kind == 'symbol-library':
        if doc.kind == 'legacy-symbol-documentation':
            return _legacy_documentation_to_sexpr_text(doc, target_version)
        return _legacy_library_to_sexpr_text(doc, target_version)
    elif target_kind == 'project':
        return _legacy_project_to_json_text(doc)
    else:
        raise ValueError('legacy KiCad conversion is not defined for this target')
    return (format_sexpr(root), warnings)

def _legacy_quote(value):
    out = '"'
    for ch in value:
        if ch == '\\' or ch == '"':
            out += '\\'
        out += ch
    return out + '"'

def _mm_to_legacy_coord(value):
    parsed = _to_float(value)
    if parsed is None:
        return 0
    return int(round(parsed / 0.0254))

def _child_atom_or_empty(node, head, index=1):
    child = node.child_list(head) if node else None
    return child.atom_at(index) if child else ''

def _child_lists(node, head):
    if not node:
        return []
    return [child for child in node.children if child.atom is None and child.head() == head]

def _symbol_pin_visibility_flag(symbol, head):
    node = symbol.child_list(head) if symbol else None
    if not node:
        return 'Y'
    if node.atom_at(1) == 'hide':
        return 'N'
    hide = node.child_list('hide')
    if hide and _bool_value(hide.atom_at(1), True):
        return 'N'
    return 'Y'

def _property_value(node, name):
    if not node:
        return ''
    for child in node.children:
        if child.atom is None and child.head() == 'property' and child.atom_at(1) == name:
            return child.atom_at(2)
    return ''

def _top_level_symbols(root):
    return [child for child in root.children if child.atom is None and child.head() == 'symbol']

def _sanitize_symbol_name(name):
    if not name:
        return 'LegacySymbol'
    out = ''
    for ch in name:
        out += '_' if ch.isspace() else ch
    return out

def _library_reference_prefix(name):
    for ch in name:
        if 'A' <= ch <= 'Z':
            return ch
    return 'U'

def _legacy_library_text_orientation(at):
    angle = _to_int(at.atom_at(3), 0) if at else 0
    angle %= 360
    return '1' if angle in {90, 270} else '0'

def _sexpr_pin_type_to_legacy(pin_type):
    return {
        'input': 'I',
        'output': 'O',
        'bidirectional': 'B',
        'tri_state': 'T',
        'power_in': 'W',
        'power_out': 'w',
        'open_collector': 'C',
        'open_emitter': 'E',
        'passive': 'P',
        'free': 'F',
        'unspecified': 'U',
        'no_connect': 'N',
    }.get(pin_type, 'U')

def _sexpr_pin_shape_to_legacy(shape):
    return {
        'inverted': 'I',
        'clock': 'C',
        'inverted_clock': 'IC',
        'input_low': 'L',
        'clock_low': 'CL',
        'output_low': 'V',
        'edge_clock_high': 'F',
        'non_logic': 'X',
    }.get(shape, '')

def _sexpr_pin_hidden(pin):
    if not pin:
        return False
    hide = pin.child_list('hide')
    if hide:
        return _bool_value(hide.atom_at(1), True)
    for child in pin.children:
        if child.atom == 'hide':
            return True
    return False

def _pin_text_size_legacy(pin, head):
    node = pin.child_list(head) if pin else None
    effects = node.child_list('effects') if node else None
    font = effects.child_list('font') if effects else None
    size = font.child_list('size') if font else None
    if size and size.atom_at(1):
        return _mm_to_legacy_coord(size.atom_at(1))
    return 50

def _sexpr_pin_angle_to_orientation(angle):
    parsed = _to_int(angle, 0) % 360
    if parsed < 0:
        parsed += 360
    if parsed == 0:
        return 'R'
    if parsed == 90:
        return 'U'
    if parsed == 180:
        return 'L'
    if parsed == 270:
        return 'D'
    return 'R'

def _stroke_width_legacy(node):
    stroke = node.child_list('stroke') if node else None
    width = stroke.child_list('width') if stroke else None
    return str(_mm_to_legacy_coord(width.atom_at(1) if width else '0'))

def _fill_legacy(node):
    fill = node.child_list('fill') if node else None
    fill_type = _child_atom_or_empty(fill, 'type') if fill else ''
    if fill_type == 'outline':
        return 'F'
    if fill_type == 'background':
        return 'f'
    return 'N'

def _effects_font_size_legacy(node):
    effects = node.child_list('effects') if node else None
    font = effects.child_list('font') if effects else None
    size = font.child_list('size') if font else None
    if size and size.atom_at(1):
        return _mm_to_legacy_coord(size.atom_at(1))
    return 50

def _font_style_legacy(node):
    effects = node.child_list('effects') if node else None
    font = effects.child_list('font') if effects else None
    bold = False
    italic = False
    for child in font.children if font else []:
        if child.atom == 'bold':
            bold = True
        elif child.atom == 'italic':
            italic = True
        elif child.atom is None and child.head() == 'bold':
            bold = _bool_value(child.atom_at(1), True)
        elif child.atom is None and child.head() == 'italic':
            italic = _bool_value(child.atom_at(1), True)
    return ('Italic' if italic else 'Normal', '1' if bold else '0')

def _legacy_subsymbol_unit_convert(name):
    parts = name.rsplit('_', 2)
    if len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():
        return (parts[1], parts[2])
    return ('1', '1')

def _symbol_legacy_unit_count(symbol):
    count = 1
    for child in symbol.children if symbol else []:
        if child.atom is None and child.head() == 'symbol':
            unit, _convert = _legacy_subsymbol_unit_convert(child.atom_at(1))
            count = max(count, _to_int(unit, 1))
    return count

def _write_legacy_pins(lines, symbol, counts, unit='1', convert='1'):
    if not symbol:
        return
    for child in symbol.children:
        if child.atom is not None:
            continue
        if child.head() == 'pin':
            at = child.child_list('at')
            length = _child_atom_or_empty(child, 'length')
            name = _child_atom_or_empty(child, 'name') or '~'
            number = _child_atom_or_empty(child, 'number') or '~'
            x = _mm_to_legacy_coord(at.atom_at(1)) if at else 0
            y = _mm_to_legacy_coord(at.atom_at(2)) if at else 0
            pin_len = _mm_to_legacy_coord(length) if length else 100
            angle = at.atom_at(3) if at else '0'
            name_size = _pin_text_size_legacy(child, 'name')
            number_size = _pin_text_size_legacy(child, 'number')
            shape = _sexpr_pin_shape_to_legacy(child.atom_at(2))
            if _sexpr_pin_hidden(child) and 'N' not in shape:
                shape += 'N'
            lines.append(
                'X {} {} {} {} {} {} {} {} {} {} {}{}'.format(
                    name,
                    number,
                    x,
                    y,
                    pin_len,
                    _sexpr_pin_angle_to_orientation(angle),
                    name_size,
                    number_size,
                    unit,
                    convert,
                    _sexpr_pin_type_to_legacy(child.atom_at(1)),
                    (' ' + shape) if shape else '',
                )
            )
            counts['pins'] += 1
        elif child.head() == 'symbol':
            child_unit, child_convert = _legacy_subsymbol_unit_convert(child.atom_at(1))
            _write_legacy_pins(lines, child, counts, child_unit, child_convert)

def _write_legacy_draw_items(lines, symbol, counts, unit='1', convert='1'):
    if not symbol:
        return
    for child in symbol.children:
        if child.atom is not None:
            continue
        head = child.head()
        if head == 'rectangle':
            start = child.child_list('start')
            end = child.child_list('end')
            if start and end:
                lines.append(
                    'S {} {} {} {} {} {} {} {}'.format(
                        _mm_to_legacy_coord(start.atom_at(1)),
                        _mm_to_legacy_coord(start.atom_at(2)),
                        _mm_to_legacy_coord(end.atom_at(1)),
                        _mm_to_legacy_coord(end.atom_at(2)),
                        unit,
                        convert,
                        _stroke_width_legacy(child),
                        _fill_legacy(child),
                    )
                )
                counts['draw'] += 1
        elif head == 'polyline':
            pts = child.child_list('pts')
            points = _child_lists(pts, 'xy')
            if points:
                parts = ['P', str(len(points)), unit, convert, _stroke_width_legacy(child)]
                for point in points:
                    parts.extend([str(_mm_to_legacy_coord(point.atom_at(1))), str(_mm_to_legacy_coord(point.atom_at(2)))])
                parts.append(_fill_legacy(child))
                lines.append(' '.join(parts))
                counts['draw'] += 1
        elif head == 'circle':
            center = child.child_list('center')
            radius = _child_atom_or_empty(child, 'radius')
            if center:
                lines.append(
                    'C {} {} {} {} {} {} {}'.format(
                        _mm_to_legacy_coord(center.atom_at(1)),
                        _mm_to_legacy_coord(center.atom_at(2)),
                        _mm_to_legacy_coord(radius),
                        unit,
                        convert,
                        _stroke_width_legacy(child),
                        _fill_legacy(child),
                    )
                )
                counts['draw'] += 1
        elif head == 'arc':
            start = child.child_list('start')
            mid = child.child_list('mid')
            end = child.child_list('end')
            if start and mid and end:
                sx = _to_float(start.atom_at(1)) or 0.0
                sy = _to_float(start.atom_at(2)) or 0.0
                mx = _to_float(mid.atom_at(1)) or 0.0
                my = _to_float(mid.atom_at(2)) or 0.0
                radius = int(round(math.hypot(sx - mx, sy - my) / 0.0254))
                lines.append(
                    'A {} {} {} 0 0 {} {} {} {} {} {} {} {}'.format(
                        _mm_to_legacy_coord(mid.atom_at(1)),
                        _mm_to_legacy_coord(mid.atom_at(2)),
                        radius,
                        unit,
                        convert,
                        _stroke_width_legacy(child),
                        _fill_legacy(child),
                        _mm_to_legacy_coord(start.atom_at(1)),
                        _mm_to_legacy_coord(start.atom_at(2)),
                        _mm_to_legacy_coord(end.atom_at(1)),
                        _mm_to_legacy_coord(end.atom_at(2)),
                    )
                )
                counts['draw'] += 1
        elif head == 'text':
            at = child.child_list('at')
            if at:
                style, bold = _font_style_legacy(child)
                lines.append(
                    'T {} {} {} {} 0 {} {} {} {} {} C C'.format(
                        _legacy_library_text_orientation(at),
                        _mm_to_legacy_coord(at.atom_at(1)),
                        _mm_to_legacy_coord(at.atom_at(2)),
                        _effects_font_size_legacy(child),
                        unit,
                        convert,
                        _legacy_quote(child.atom_at(1)),
                        style,
                        bold,
                    )
                )
                counts['draw'] += 1
        elif head == 'symbol':
            child_unit, child_convert = _legacy_subsymbol_unit_convert(child.atom_at(1))
            _write_legacy_draw_items(lines, child, counts, child_unit, child_convert)

def _legacy_documentation_sidecar_text(doc, target_major, warnings):
    lines = ['EESchema-DOCLIB  Version 2.0']
    count = 0
    if doc.kind == 'symbol-library' and doc.root:
        for symbol in _top_level_symbols(doc.root):
            name = _sanitize_symbol_name(symbol.atom_at(1))
            lines.append('$CMP ' + name)
            lines.append('D ' + _property_value(symbol, 'Description'))
            lines.append('K ' + _property_value(symbol, 'ki_keywords'))
            lines.append('F ' + _property_value(symbol, 'Datasheet'))
            lines.append('$ENDCMP')
            count += 1
    lines.append('#')
    lines.append('#End Doc Library')
    if count > 0:
        warnings.append('wrote legacy .dcm sidecar for symbol documentation properties')
    else:
        warnings.append('wrote empty legacy .dcm sidecar')
    return '\n'.join(lines) + '\n'

def _property_hidden(node):
    if not node:
        return False
    hide = node.child_list('hide')
    if hide:
        return _bool_value(hide.atom_at(1), True)
    effects = node.child_list('effects')
    if effects:
        for child in effects.children:
            if child.atom == 'hide':
                return True
    return False

def _legacy_library_field_orientation(at):
    angle = _to_int(at.atom_at(3), 0) if at else 0
    angle %= 360
    return 'V' if angle in {90, 270} else 'H'

def _legacy_library_standard_property_field(symbol, index, name, default_hidden=True):
    prop = None
    for child in symbol.children if symbol else []:
        if child.atom is None and child.head() == 'property' and child.atom_at(1) == name:
            prop = child
            break
    at = prop.child_list('at') if prop else None
    x = _mm_to_legacy_coord(at.atom_at(1)) if at else 0
    y = _mm_to_legacy_coord(at.atom_at(2)) if at else 0
    hidden = _property_hidden(prop) if prop else default_hidden
    return 'F{} {} {} {} 50 {} {} C CNN'.format(
        index,
        _legacy_quote(prop.atom_at(2) if prop else ''),
        x,
        y,
        _legacy_library_field_orientation(at),
        'I' if hidden else 'V',
    )

def _legacy_library_custom_property_fields(symbol):
    skip = {'Reference', 'Value', 'Footprint', 'Datasheet', 'Description', 'ki_description', 'ki_keywords'}
    fields = []
    index = 4
    for child in symbol.children if symbol else []:
        if child.atom is None and child.head() == 'property' and child.atom_at(1) not in skip:
            at = child.child_list('at')
            x = _mm_to_legacy_coord(at.atom_at(1)) if at else 0
            y = _mm_to_legacy_coord(at.atom_at(2)) if at else 0
            fields.append(
                'F{} {} {} {} 50 {} {} C CNN {}'.format(
                    index,
                    _legacy_quote(child.atom_at(2)),
                    x,
                    y,
                    _legacy_library_field_orientation(at),
                    'I' if _property_hidden(child) else 'V',
                    _legacy_quote(child.atom_at(1)),
                )
            )
            index += 1
    return fields

def _sexpr_symbol_library_to_legacy(doc, target_major, warnings):
    lines = [
        'EESchema-LIBRARY Version {}'.format('2.3' if target_major <= 4 else '2.4'),
        '#encoding utf-8',
    ]
    counts = {'symbols': 0, 'pins': 0, 'draw': 0, 'aliases': 0}
    aliases_by_base = {}
    for symbol in _top_level_symbols(doc.root):
        base = _child_atom_or_empty(symbol, 'extends')
        if base:
            aliases_by_base.setdefault(base, []).append(_sanitize_symbol_name(symbol.atom_at(1)))
    for symbol in _top_level_symbols(doc.root):
        if _child_atom_or_empty(symbol, 'extends'):
            continue
        name = _sanitize_symbol_name(symbol.atom_at(1))
        reference = _property_value(symbol, 'Reference') or _library_reference_prefix(name)
        show_pin_numbers = _symbol_pin_visibility_flag(symbol, 'pin_numbers')
        show_pin_names = _symbol_pin_visibility_flag(symbol, 'pin_names')
        unit_count = _symbol_legacy_unit_count(symbol)
        lines.extend(['#', '# ' + name, '#'])
        lines.append('DEF {} {} 0 40 {} {} {} F N'.format(name, reference, show_pin_numbers, show_pin_names, unit_count))
        aliases = aliases_by_base.get(name, [])
        if aliases:
            lines.append('ALIAS ' + ' '.join(aliases))
            counts['aliases'] += len(aliases)
        lines.append('F0 {} 0 0 50 H V C CNN'.format(_legacy_quote(reference)))
        lines.append('F1 {} 0 -100 50 H V C CNN'.format(_legacy_quote(name)))
        lines.append(_legacy_library_standard_property_field(symbol, 2, 'Footprint', True))
        lines.append(_legacy_library_standard_property_field(symbol, 3, 'Datasheet', True))
        lines.extend(_legacy_library_custom_property_fields(symbol))
        lines.append('DRAW')
        _write_legacy_draw_items(lines, symbol, counts)
        _write_legacy_pins(lines, symbol, counts)
        lines.append('ENDDRAW')
        lines.append('ENDDEF')
        counts['symbols'] += 1
    lines.extend(['#', '#End Library'])
    if counts['symbols'] == 0:
        warnings.append('converted empty symbol library to legacy .lib')
    else:
        warnings.append('converted symbol definitions to legacy .lib headers; drawing primitives and pins are lossy')
    if counts['pins'] > 0:
        warnings.append('converted symbol pins to legacy X records')
    if counts['draw'] > 0:
        warnings.append('converted symbol drawing primitives to legacy DRAW records')
    if counts['aliases'] > 0:
        warnings.append('converted symbol aliases to legacy ALIAS records')
    dcm = _legacy_documentation_sidecar_text(doc, target_major, warnings)
    return ('\n'.join(lines) + '\n', dcm)

def _property_node_by_name(node, name):
    if not node:
        return None
    for child in node.children:
        if child.atom is None and child.head() == 'property' and child.atom_at(1) == name:
            return child
    return None

def _property_value_any(node, names):
    for name in names:
        value = _property_value(node, name)
        if value:
            return value
    return ''

def _sexpr_angle_to_legacy_text_orientation(angle):
    parsed = _to_int(angle, 0) % 360
    if parsed < 0:
        parsed += 360
    if parsed == 90:
        return '1'
    if parsed == 180:
        return '2'
    if parsed == 270:
        return '3'
    return '0'

def _sexpr_label_shape_to_legacy(shape):
    return {
        'input': 'Input',
        'output': 'Output',
        'bidirectional': 'BiDi',
        'tri_state': 'TriState',
    }.get(shape, 'UnSpc')

def _sexpr_sheet_pin_type_to_legacy(pin_type):
    return {
        'input': 'I',
        'output': 'O',
        'bidirectional': 'B',
        'tri_state': 'T',
    }.get(pin_type, 'U')

def _replace_trailing_extension(value, old, new):
    if value.lower().endswith(old.lower()):
        return value[:-len(old)] + new
    return value

def _is_legacy_tstamp(value):
    if len(value) != 8:
        return False
    for ch in value:
        if ch not in '0123456789abcdefABCDEF':
            return False
    return True

def _legacy_tstamp(value, seed):
    if _is_legacy_tstamp(value):
        return value.upper()
    digest = hashlib.sha1(seed.encode('utf-8')).hexdigest()
    return digest[:8].upper()

def _schematic_meta_from_sexpr(root):
    meta = {
        'paper': _child_atom_or_empty(root, 'paper') or 'A4',
        'title': '',
        'date': '',
        'rev': '',
        'company': '',
        'comments': [''] * 9,
    }
    title = root.child_list('title_block') if root else None
    if not title:
        return meta
    meta['title'] = _child_atom_or_empty(title, 'title')
    meta['date'] = _child_atom_or_empty(title, 'date')
    meta['rev'] = _child_atom_or_empty(title, 'rev')
    meta['company'] = _child_atom_or_empty(title, 'company')
    for child in title.children:
        if child.atom is None and child.head() == 'comment' and child.atom_at(1).isdigit():
            index = int(child.atom_at(1))
            if 1 <= index <= 9:
                meta['comments'][index - 1] = child.atom_at(2)
    return meta

def _schematic_legacy_library_names(root, path):
    names = []
    for child in root.children if root else []:
        if child.atom is None and child.head() == 'symbol':
            lib_id = _child_atom_or_empty(child, 'lib_id')
            if ':' in lib_id:
                name = _sanitize_symbol_name(lib_id.split(':', 1)[0])
                if name and name not in names:
                    names.append(name)
    if not names:
        fallback = _sanitize_symbol_name(path.stem)
        if fallback:
            names.append(fallback)
    return names

def _legacy_schematic_component_lib_id(lib_id, path, target_major):
    if ':' in lib_id:
        library, symbol = lib_id.split(':', 1)
        return _sanitize_symbol_name(library) + ':' + _sanitize_symbol_name(symbol)
    return _sanitize_symbol_name(lib_id)

def _legacy_field_orientation(at):
    angle = _to_int(at.atom_at(3), 0) if at else 0
    angle %= 360
    return 'V' if angle in {90, 270} else 'H'

def _write_legacy_schematic_field(lines, index, symbol, name, value, fallback_x, fallback_y, hidden):
    prop = _property_node_by_name(symbol, name)
    at = prop.child_list('at') if prop else None
    x = _mm_to_legacy_coord(at.atom_at(1)) if at else fallback_x
    y = _mm_to_legacy_coord(at.atom_at(2)) if at else fallback_y
    size = _effects_font_size_legacy(prop) if prop else 50
    hidden_flag = _property_hidden(prop) if prop else hidden
    lines.append(
        'F {} {} {} {} {} {}  {} C CNN'.format(
            index,
            _legacy_quote(value),
            _legacy_field_orientation(at),
            x,
            y,
            size,
            '0001' if hidden_flag else '0000',
        )
    )

def _write_legacy_schematic_custom_fields(lines, symbol, fallback_x, fallback_y):
    standard = {'Reference', 'Value', 'Footprint', 'Datasheet'}
    used = {0, 1, 2, 3}
    pending = []
    next_index = 4
    for child in symbol.children if symbol else []:
        if child.atom is not None or child.head() != 'property':
            continue
        name = child.atom_at(1)
        if name in standard or name.startswith('ki_'):
            continue
        prop_id = _child_atom_or_empty(child, 'id')
        index = _to_int(prop_id, -1) if prop_id else -1
        if index < 4 or index in used:
            while next_index in used:
                next_index += 1
            index = next_index
        used.add(index)
        pending.append((index, child))
    for index, prop in sorted(pending, key=lambda item: item[0]):
        at = prop.child_list('at')
        x = _mm_to_legacy_coord(at.atom_at(1)) if at else fallback_x
        y = _mm_to_legacy_coord(at.atom_at(2)) if at else fallback_y
        lines.append(
            'F {} {} {} {} {} {}  {} C CNN {}'.format(
                index,
                _legacy_quote(prop.atom_at(2)),
                _legacy_field_orientation(at),
                x,
                y,
                _effects_font_size_legacy(prop),
                '0001' if _property_hidden(prop) else '0000',
                _legacy_quote(prop.atom_at(1)),
            )
        )

def _legacy_symbol_transform(symbol):
    at = symbol.child_list('at') if symbol else None
    angle = _to_int(at.atom_at(3), 0) if at else 0
    angle %= 360
    if angle == 90:
        transform = [0, -1, -1, 0]
    elif angle == 180:
        transform = [-1, 0, 0, 1]
    elif angle == 270:
        transform = [0, 1, 1, 0]
    else:
        transform = [1, 0, 0, -1]
    mirror = _child_atom_or_empty(symbol, 'mirror')
    if mirror == 'x':
        transform[2] = -transform[2]
        transform[3] = -transform[3]
    elif mirror == 'y':
        transform[0] = -transform[0]
        transform[1] = -transform[1]
    return tuple(transform)

def _points_xy(node):
    pts = node.child_list('pts') if node else None
    return _child_lists(pts, 'xy')

def _append_legacy_notes_line(lines, x1, y1, x2, y2):
    lines.append('Wire Notes Line')
    lines.append(
        '\t{} {} {} {}'.format(
            _mm_to_legacy_coord(x1),
            _mm_to_legacy_coord(y1),
            _mm_to_legacy_coord(x2),
            _mm_to_legacy_coord(y2),
        )
    )

def _append_legacy_notes_circle(lines, center, radius, segments=16):
    cx = _to_float(center.atom_at(1)) if center else None
    cy = _to_float(center.atom_at(2)) if center else None
    r = _to_float(radius)
    if cx is None or cy is None or r is None or r <= 0:
        return 0
    points = []
    for index in range(segments):
        angle = 2.0 * math.pi * index / segments
        points.append((cx + math.cos(angle) * r, cy + math.sin(angle) * r))
    for index in range(segments):
        x1, y1 = points[index]
        x2, y2 = points[(index + 1) % segments]
        _append_legacy_notes_line(lines, _format_float(x1), _format_float(y1), _format_float(x2), _format_float(y2))
    return segments

def _append_legacy_notes_arc(lines, start, mid, end):
    sx = _to_float(start.atom_at(1)) if start else None
    sy = _to_float(start.atom_at(2)) if start else None
    mx = _to_float(mid.atom_at(1)) if mid else None
    my = _to_float(mid.atom_at(2)) if mid else None
    ex = _to_float(end.atom_at(1)) if end else None
    ey = _to_float(end.atom_at(2)) if end else None
    if sx is None or sy is None or mx is None or my is None or ex is None or ey is None:
        return 0
    det = 2.0 * (sx * (my - ey) + mx * (ey - sy) + ex * (sy - my))
    if abs(det) < 1e-9:
        _append_legacy_notes_line(lines, _format_float(sx), _format_float(sy), _format_float(mx), _format_float(my))
        _append_legacy_notes_line(lines, _format_float(mx), _format_float(my), _format_float(ex), _format_float(ey))
        return 2
    s2 = sx * sx + sy * sy
    m2 = mx * mx + my * my
    e2 = ex * ex + ey * ey
    cx = (s2 * (my - ey) + m2 * (ey - sy) + e2 * (sy - my)) / det
    cy = (s2 * (ex - mx) + m2 * (sx - ex) + e2 * (mx - sx)) / det
    radius = math.hypot(sx - cx, sy - cy)
    if radius <= 0:
        return 0
    start_angle = math.atan2(sy - cy, sx - cx)
    mid_angle = math.atan2(my - cy, mx - cx)
    end_angle = math.atan2(ey - cy, ex - cx)
    full = 2.0 * math.pi
    ccw_total = (end_angle - start_angle) % full
    ccw_mid = (mid_angle - start_angle) % full
    total = ccw_total if ccw_mid <= ccw_total else ccw_total - full
    segments = max(2, min(24, int(abs(total) / (math.pi / 8.0)) + 1))
    previous = (sx, sy)
    for index in range(1, segments + 1):
        angle = start_angle + total * index / segments
        current = (cx + math.cos(angle) * radius, cy + math.sin(angle) * radius)
        _append_legacy_notes_line(lines, _format_float(previous[0]), _format_float(previous[1]), _format_float(current[0]), _format_float(current[1]))
        previous = current
    return segments

def _xy_float_tuple(node):
    if not node:
        return None
    x = _to_float(node.atom_at(1))
    y = _to_float(node.atom_at(2))
    if x is None or y is None:
        return None
    return (x, y)

def _append_legacy_notes_bezier(lines, xy_nodes, segments=16):
    points = []
    for xy in xy_nodes:
        point = _xy_float_tuple(xy)
        if point is not None:
            points.append(point)
    if len(points) < 2:
        return 0
    if len(points) not in {3, 4}:
        for index in range(len(points) - 1):
            _append_legacy_notes_line(
                lines,
                _format_float(points[index][0]),
                _format_float(points[index][1]),
                _format_float(points[index + 1][0]),
                _format_float(points[index + 1][1]),
            )
        return len(points) - 1
    previous = points[0]
    for index in range(1, segments + 1):
        t = float(index) / segments
        u = 1.0 - t
        if len(points) == 3:
            x = u * u * points[0][0] + 2.0 * u * t * points[1][0] + t * t * points[2][0]
            y = u * u * points[0][1] + 2.0 * u * t * points[1][1] + t * t * points[2][1]
        else:
            x = (
                u * u * u * points[0][0]
                + 3.0 * u * u * t * points[1][0]
                + 3.0 * u * t * t * points[2][0]
                + t * t * t * points[3][0]
            )
            y = (
                u * u * u * points[0][1]
                + 3.0 * u * u * t * points[1][1]
                + 3.0 * u * t * t * points[2][1]
                + t * t * t * points[3][1]
            )
        _append_legacy_notes_line(lines, _format_float(previous[0]), _format_float(previous[1]), _format_float(x), _format_float(y))
        previous = (x, y)
    return segments

def _sexpr_schematic_to_legacy(doc, target_major, warnings):
    root = doc.root
    meta = _schematic_meta_from_sexpr(root)
    version = 2 if target_major <= 4 else 4
    lines = ['EESchema Schematic File Version {}'.format(version)]
    for library in _schematic_legacy_library_names(root, doc.path):
        lines.append('LIBS:' + library)
    lines.extend([
        'EELAYER 30 0',
        'EELAYER END',
        '$Descr {} 11693 8268'.format(meta['paper'] or 'A4'),
        'encoding utf-8',
        'Sheet 1 1',
        'Title ' + _legacy_quote(meta['title']),
        'Date ' + _legacy_quote(meta['date']),
        'Rev ' + _legacy_quote(meta['rev']),
        'Comp ' + _legacy_quote(meta['company']),
    ])
    for index, comment in enumerate(meta['comments'], 1):
        lines.append('Comment{} {}'.format(index, _legacy_quote(comment)))
    lines.append('$EndDescr')
    counts = {
        'symbols': 0,
        'wires': 0,
        'sheets': 0,
        'labels': 0,
        'junctions': 0,
        'no_connects': 0,
        'buses': 0,
        'bus_entries': 0,
        'sheet_pins': 0,
        'drawings': 0,
    }
    for child in root.children if root else []:
        if child.atom is not None:
            continue
        head = child.head()
        if head in {'wire', 'bus'}:
            xy = _points_xy(child)
            if len(xy) < 2:
                continue
            lines.append('Wire {} Line'.format('Bus' if head == 'bus' else 'Wire'))
            lines.append(
                '\t{} {} {} {}'.format(
                    _mm_to_legacy_coord(xy[0].atom_at(1)),
                    _mm_to_legacy_coord(xy[0].atom_at(2)),
                    _mm_to_legacy_coord(xy[1].atom_at(1)),
                    _mm_to_legacy_coord(xy[1].atom_at(2)),
                )
            )
            counts['buses' if head == 'bus' else 'wires'] += 1
        elif head == 'bus_entry':
            at = child.child_list('at')
            size = child.child_list('size')
            if not at or not size:
                continue
            x = _mm_to_legacy_coord(at.atom_at(1))
            y = _mm_to_legacy_coord(at.atom_at(2))
            x2 = x + _mm_to_legacy_coord(size.atom_at(1))
            y2 = y + _mm_to_legacy_coord(size.atom_at(2))
            lines.append('Entry Wire Line')
            lines.append('\t{} {} {} {}'.format(x, y, x2, y2))
            counts['bus_entries'] += 1
        elif head == 'polyline':
            xy = _points_xy(child)
            if len(xy) < 2:
                continue
            for index in range(len(xy) - 1):
                _append_legacy_notes_line(lines, xy[index].atom_at(1), xy[index].atom_at(2), xy[index + 1].atom_at(1), xy[index + 1].atom_at(2))
                counts['drawings'] += 1
        elif head == 'bezier':
            drawn = _append_legacy_notes_bezier(lines, _points_xy(child))
            counts['drawings'] += drawn
        elif head == 'rectangle':
            start = child.child_list('start')
            end = child.child_list('end')
            if not start or not end:
                continue
            x1 = start.atom_at(1)
            y1 = start.atom_at(2)
            x2 = end.atom_at(1)
            y2 = end.atom_at(2)
            _append_legacy_notes_line(lines, x1, y1, x2, y1)
            _append_legacy_notes_line(lines, x2, y1, x2, y2)
            _append_legacy_notes_line(lines, x2, y2, x1, y2)
            _append_legacy_notes_line(lines, x1, y2, x1, y1)
            counts['drawings'] += 4
        elif head == 'circle':
            center = child.child_list('center')
            drawn = _append_legacy_notes_circle(lines, center, _child_atom_or_empty(child, 'radius'))
            counts['drawings'] += drawn
        elif head == 'arc':
            drawn = _append_legacy_notes_arc(lines, child.child_list('start'), child.child_list('mid'), child.child_list('end'))
            counts['drawings'] += drawn
        elif head == 'junction':
            at = child.child_list('at')
            if at:
                lines.append('Connection ~ {} {}'.format(_mm_to_legacy_coord(at.atom_at(1)), _mm_to_legacy_coord(at.atom_at(2))))
                counts['junctions'] += 1
        elif head == 'no_connect':
            at = child.child_list('at')
            if at:
                lines.append('NoConn ~ {} {}'.format(_mm_to_legacy_coord(at.atom_at(1)), _mm_to_legacy_coord(at.atom_at(2))))
                counts['no_connects'] += 1
        elif head in {'label', 'global_label', 'hierarchical_label', 'directive_label', 'netclass_flag', 'text', 'text_box'}:
            at = child.child_list('at')
            if not at:
                continue
            legacy_type = 'Notes'
            if head == 'label':
                legacy_type = 'Label'
            elif head == 'global_label':
                legacy_type = 'GLabel'
            elif head == 'hierarchical_label':
                legacy_type = 'HLabel'
            line = 'Text {} {} {} {} {}'.format(
                legacy_type,
                _mm_to_legacy_coord(at.atom_at(1)),
                _mm_to_legacy_coord(at.atom_at(2)),
                _sexpr_angle_to_legacy_text_orientation(at.atom_at(3)),
                _effects_font_size_legacy(child),
            )
            if legacy_type in {'GLabel', 'HLabel'}:
                line += ' ' + _sexpr_label_shape_to_legacy(_child_atom_or_empty(child, 'shape'))
            lines.append(line + ' ~ 0')
            lines.append(child.atom_at(1))
            counts['labels'] += 1
            if head == 'text_box':
                size = child.child_list('size')
                x = _to_float(at.atom_at(1))
                y = _to_float(at.atom_at(2))
                w = _to_float(size.atom_at(1)) if size else None
                h = _to_float(size.atom_at(2)) if size else None
                if x is not None and y is not None and w is not None and h is not None and w and h:
                    x2 = x + w
                    y2 = y + h
                    _append_legacy_notes_line(lines, _format_float(x), _format_float(y), _format_float(x2), _format_float(y))
                    _append_legacy_notes_line(lines, _format_float(x2), _format_float(y), _format_float(x2), _format_float(y2))
                    _append_legacy_notes_line(lines, _format_float(x2), _format_float(y2), _format_float(x), _format_float(y2))
                    _append_legacy_notes_line(lines, _format_float(x), _format_float(y2), _format_float(x), _format_float(y))
                    counts['drawings'] += 4
        elif head == 'sheet':
            at = child.child_list('at')
            size = child.child_list('size')
            if not at or not size:
                continue
            sheet_name = _property_value_any(child, ['Sheet name', 'Sheetname'])
            sheet_file = _property_value_any(child, ['Sheet file', 'Sheetfile'])
            uuid = _child_atom_or_empty(child, 'tstamp') or _child_atom_or_empty(child, 'uuid')
            uuid = _legacy_tstamp(uuid, str(doc.path) + ':sheet:' + sheet_file)
            if not sheet_name and sheet_file:
                sheet_name = _replace_trailing_extension(sheet_file, '.kicad_sch', '')
            if not sheet_name:
                sheet_name = 'Sheet_' + uuid
            if not sheet_file:
                sheet_file = sheet_name + '.sch'
            else:
                sheet_file = _replace_trailing_extension(sheet_file, '.kicad_sch', '.sch')
            lines.append('$Sheet')
            lines.append(
                'S {} {} {} {}'.format(
                    _mm_to_legacy_coord(at.atom_at(1)),
                    _mm_to_legacy_coord(at.atom_at(2)),
                    _mm_to_legacy_coord(size.atom_at(1)),
                    _mm_to_legacy_coord(size.atom_at(2)),
                )
            )
            lines.append('U ' + uuid)
            sheet_name_prop = _property_node_by_name(child, 'Sheet name') or _property_node_by_name(child, 'Sheetname')
            sheet_file_prop = _property_node_by_name(child, 'Sheet file') or _property_node_by_name(child, 'Sheetfile')
            lines.append('F0 {} {}'.format(_legacy_quote(sheet_name), _effects_font_size_legacy(sheet_name_prop) if sheet_name_prop else 50))
            lines.append('F1 {} {}'.format(_legacy_quote(sheet_file), _effects_font_size_legacy(sheet_file_prop) if sheet_file_prop else 50))
            field_index = 2
            for pin in child.children:
                if pin.atom is not None or pin.head() != 'pin':
                    continue
                pin_at = pin.child_list('at')
                if not pin_at:
                    continue
                lines.append(
                    'F{} {} {} {} {} {} {}'.format(
                        field_index,
                        _legacy_quote(pin.atom_at(1)),
                        _sexpr_sheet_pin_type_to_legacy(_child_atom_or_empty(pin, 'type')),
                        _sexpr_pin_angle_to_orientation(pin_at.atom_at(3)),
                        _mm_to_legacy_coord(pin_at.atom_at(1)),
                        _mm_to_legacy_coord(pin_at.atom_at(2)),
                        _effects_font_size_legacy(pin),
                    )
                )
                field_index += 1
                counts['sheet_pins'] += 1
            lines.append('$EndSheet')
            counts['sheets'] += 1
        elif head == 'symbol':
            lib_id = _child_atom_or_empty(child, 'lib_id')
            if not lib_id:
                continue
            legacy_symbol_name = _legacy_schematic_component_lib_id(lib_id, doc.path, target_major)
            reference = _property_value(child, 'Reference') or _library_reference_prefix(lib_id)
            value = _property_value(child, 'Value') or lib_id
            footprint = _property_value(child, 'Footprint')
            datasheet = _property_value(child, 'Datasheet')
            unit = _child_atom_or_empty(child, 'unit') or '1'
            at = child.child_list('at')
            x = _mm_to_legacy_coord(at.atom_at(1)) if at else 0
            y = _mm_to_legacy_coord(at.atom_at(2)) if at else 0
            stamp = _child_atom_or_empty(child, 'tstamp') or _child_atom_or_empty(child, 'uuid')
            stamp = _legacy_tstamp(stamp, str(doc.path) + ':' + reference + ':' + lib_id)
            transform = _legacy_symbol_transform(child)
            lines.append('$Comp')
            lines.append('L {} {}'.format(legacy_symbol_name, reference))
            lines.append('U {} 1 {}'.format(unit, stamp))
            lines.append('P {} {}'.format(x, y))
            _write_legacy_schematic_field(lines, 0, child, 'Reference', reference, x, y, False)
            _write_legacy_schematic_field(lines, 1, child, 'Value', value, x, y + 100, False)
            _write_legacy_schematic_field(lines, 2, child, 'Footprint', footprint, x, y, True)
            _write_legacy_schematic_field(lines, 3, child, 'Datasheet', datasheet, x, y, True)
            _write_legacy_schematic_custom_fields(lines, child, x, y)
            lines.append('\t1    {} {}'.format(x, y))
            lines.append('\t{}    {}    {}    {}'.format(transform[0], transform[1], transform[2], transform[3]))
            lines.append('$EndComp')
            counts['symbols'] += 1
    lines.append('$EndSCHEMATC')
    if counts['symbols']:
        warnings.append('converted schematic symbols to legacy $Comp records')
    if counts['wires']:
        warnings.append('converted schematic wires to legacy Wire records')
    if counts['sheets']:
        warnings.append('converted schematic sheets to legacy $Sheet records')
    if counts['labels']:
        warnings.append('converted schematic labels/text to legacy Text records')
    if counts['junctions']:
        warnings.append('converted schematic junctions to legacy Connection records')
    if counts['no_connects']:
        warnings.append('converted schematic no-connects to legacy NoConn records')
    if counts['buses']:
        warnings.append('converted schematic buses to legacy Wire Bus records')
    if counts['bus_entries']:
        warnings.append('converted schematic bus entries to legacy Entry records')
    if counts['sheet_pins']:
        warnings.append('converted schematic sheet pins to legacy sheet fields')
    if counts['drawings']:
        warnings.append('converted schematic graphic shapes to legacy Wire Notes records')
    warnings.append('converted schematic page metadata to legacy .sch; modern objects are lossy')
    return '\n'.join(lines) + '\n'

def convert_sexpr_to_legacy_text(doc, target_major):
    warnings = ['converted S-expression document to a minimal KiCad legacy file; detailed legacy record conversion is still limited']
    if doc.kind == 'schematic':
        warnings = []
        text = _sexpr_schematic_to_legacy(doc, target_major, warnings)
        return (text, 'legacy-schematic', warnings, None)
    if doc.kind == 'symbol-library':
        warnings = []
        text, dcm = _sexpr_symbol_library_to_legacy(doc, target_major, warnings)
        return (text, 'legacy-symbol-library', warnings, dcm)
    if doc.kind == 'project':
        text, project_warnings = _project_json_to_legacy_text(doc)
        return (text, 'legacy-project', project_warnings, None)
    raise ValueError('legacy writer is not defined for this file type')

def normalize_file(input_path, output_path, target):
    doc = load_document(input_path)
    report = FileReport(str(output_path), doc.kind, doc.version)
    target_major = target_major_version(target)
    if doc.kind.startswith('legacy-'):
        if target_major <= 5:
            text, warnings = rewrite_legacy_text_for_target(doc, target_major)
            report.warnings = warnings
            report.target_version = legacy_target_version_for_kind(doc.kind, target_major)
            report.changed = True
            output_path.parent.mkdir(parents=True, exist_ok=True)
            _write_text(output_path, text)
            return report
        target_kind = SEXPR_KIND_FOR_LEGACY.get(doc.kind)
        if target_kind == 'project':
            resolved = 'kicad-project-json'
        elif target_kind:
            resolved = resolve_target_version(target_kind, target)
        else:
            raise ValueError('legacy KiCad conversion is not defined for this target')
        text, warnings = convert_legacy_to_sexpr_text(doc, resolved, target_kind)
        report.kind = target_kind
        report.warnings = warnings
        report.target_version = resolved
        report.changed = True
        output_path.parent.mkdir(parents=True, exist_ok=True)
        _write_text(output_path, text)
        return report
    if target_major <= 5 and doc.kind in LEGACY_KIND_FOR_SEXPR:
        text, target_kind, warnings, dcm_text = convert_sexpr_to_legacy_text(doc, target_major)
        report.kind = target_kind
        report.warnings = warnings
        report.target_version = legacy_target_version_for_kind(doc.kind, target_major)
        report.changed = True
        output_path.parent.mkdir(parents=True, exist_ok=True)
        _write_text(output_path, text)
        if dcm_text is not None:
            _write_text(output_path.with_suffix('.dcm'), dcm_text)
        return report
    if doc.kind == 'project':
        if input_path.resolve() != output_path.resolve():
            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(input_path, output_path)
        report.target_version = 'kicad-project-json'
        return report
    resolved = resolve_target_version(doc.kind, target)
    source = int(doc.version) if _is_number(doc.version) else 0
    target_int = int(resolved)
    if source and source == target_int:
        if input_path.resolve() != output_path.resolve():
            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(input_path, output_path)
        report.target_version = resolved
        return report
    if source and source < target_int:
        report.warnings = apply_upgrade_rules(doc, target_int)
    else:
        report.warnings = apply_downgrade_rules(doc, target_int)
    ensure_version(doc, resolved)
    report.target_version = doc.version
    report.changed = True
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('w', encoding='utf-8', newline='') as out:
        out.write(format_sexpr(doc.root))
    return report

def _default_legacy_visible_items():
    return [
        0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18,
        19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 32, 33, 34, 35,
        36, 37, 38, 39, 40, 41,
    ]

def _legacy_visible_item_id(name):
    ids = {
        'vias': 0,
        'via_holes': 1,
        'through_via_holes': 1,
        'blind_buried_via_holes': 2,
        'micro_via_holes': 3,
        'non_plated_holes': 4,
        'drill_holes': 5,
        'footprint_text': 6,
        'footprint_anchors': 8,
        'ratsnest': 11,
        'grid': 12,
        'footprints_front': 15,
        'footprints_back': 16,
        'footprint_values': 17,
        'footprint_references': 18,
        'tracks': 19,
        'drc_errors': 20,
        'drawing_sheet': 23,
        'bitmaps': 24,
        'pads': 30,
        'zones': 32,
        'drc_warnings': 33,
        'drc_exclusions': 36,
        'locked_item_shadows': 37,
        'ly_points': 38,
        'conflict_shadows': 39,
        'shapes': 40,
        'board_outline_area': 41,
    }
    return ids.get(name, -1)

def _legacy_visible_items_from_source(source_path):
    if not source_path or not source_path.exists():
        return []
    try:
        data = json.loads(source_path.read_text(encoding='utf-8-sig'))
        items = data.get('board', {}).get('visible_items', [])
    except Exception:
        return []
    result = []
    seeded_defaults = False
    for item in items:
        if isinstance(item, int):
            item_id = item
        elif isinstance(item, str) and item.isdigit():
            item_id = int(item)
        else:
            if not seeded_defaults:
                explicit = list(result)
                result = _default_legacy_visible_items()
                for explicit_item in explicit:
                    if explicit_item not in result:
                        result.append(explicit_item)
                seeded_defaults = True
            item_id = _legacy_visible_item_id(str(item))
        if item_id >= 0 and item_id not in result:
            result.append(item_id)
    return result

def _visible_layers_from_source(source_path):
    if not source_path or not source_path.exists():
        return ''
    try:
        data = json.loads(source_path.read_text(encoding='utf-8-sig'))
        return str(data.get('board', {}).get('visible_layers', ''))
    except Exception:
        return ''

def _normalize_legacy_visible_layers(value):
    digits = ''
    for ch in value:
        if ch == '_':
            continue
        if ch.lower() not in '0123456789abcdef':
            return ''
        digits += ch.lower()
    if not digits:
        return ''
    if len(digits) > 15:
        digits = digits[-15:]
    elif len(digits) < 15:
        digits = '0' * (15 - len(digits)) + digits
    return digits[:7] + '_' + digits[7:]

def ensure_legacy_project_local_settings(path, suffix, source_path=None):
    meta_version = 3 if suffix in {'V6', 'V7', 'V8'} else 4
    visible_items = _legacy_visible_items_from_source(source_path) or _default_legacy_visible_items()
    visible_layers = _normalize_legacy_visible_layers(_visible_layers_from_source(source_path))
    if not visible_layers:
        visible_layers = 'fffffff_ffffffff'
    payload = {'board': {'visible_items': visible_items, 'visible_layers': 'ffffffff_ffffffff_ffffffff_ffffffff'}, 'meta': {'filename': path.name, 'version': meta_version}}
    payload['board']['visible_layers'] = visible_layers
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def _replace_extension(path, suffix):
    return path.with_suffix(suffix)

def format_reports_json(reports):
    data = {'files': [{'path': r.path, 'kind': r.kind, 'source_version': r.source_version, **({'target_version': r.target_version} if r.target_version else {}), 'changed': r.changed, **({'warnings': r.warnings} if r.warnings else {})} for r in reports]}
    return json.dumps(data, ensure_ascii=False, indent=2) + '\n'

def convert(input_path, output_path, target, report_path=None):
    input_p = Path(input_path)
    output_p = versioned_output_path(output_path, target)
    reports = []
    stderr_lines = []
    if input_p.is_dir() or input_p.suffix.lower() in {'.kicad_pro', '.pro'}:
        src_dir = input_p if input_p.is_dir() else input_p.parent
        copied = copy_project_tree(src_dir, output_p, target)
        for src_path, path in copied:
            if is_kicad_document_path(src_path):
                report = normalize_file(src_path, path, target)
                reports.append(report)
                stderr_lines.extend((f'warning: {path}: {warning}' for warning in report.warnings))
        suffix = target_version_suffix(target)
        if suffix in {'V6', 'V7', 'V8'}:
            for src_path, path in copied:
                if path.suffix.lower() == '.kicad_pcb':
                    ensure_legacy_project_local_settings(
                        _replace_extension(path, '.kicad_prl'),
                        suffix,
                        _replace_extension(src_path, '.kicad_prl'),
                    )
        target_major = target_major_version(target)
        if target_major <= 6:
            table_reports = normalize_project_library_tables(copied, target_major)
            reports.extend(table_reports)
            for table_report in table_reports:
                stderr_lines.extend((f'warning: {table_report.path}: {warning}' for warning in table_report.warnings))
        if target_major > 5:
            rebuilt = rebuild_kicad6_project_hierarchy_instances(copied)
            if rebuilt:
                hierarchy_report = _report(
                    output_p,
                    'schematic-hierarchy',
                    'project-local',
                    'modern-compatible',
                    True,
                    ['rebuilt KiCad 6+ schematic sheet/symbol hierarchy instances in {} file(s)'.format(rebuilt)],
                )
                reports.append(hierarchy_report)
                stderr_lines.extend((f'warning: {hierarchy_report.path}: {warning}' for warning in hierarchy_report.warnings))
            project_dirs = set()
            for _src_path, path in copied:
                if path.suffix.lower() == '.kicad_sym':
                    project_dirs.add(path.parent)
            for project_dir in sorted(project_dirs):
                table_report = ensure_project_local_symbol_library_table(project_dir, copied, target_major)
                embed_warnings = []
                embedded = embed_project_local_schematic_symbols(project_dir, copied, embed_warnings)
                if embedded > 0:
                    table_report.changed = True
                    table_report.warnings.append('embedded generated schematic symbols for standalone loading')
                table_report.warnings.extend(embed_warnings)
                reports.append(table_report)
                stderr_lines.extend((f'warning: {table_report.path}: {warning}' for warning in table_report.warnings))
    else:
        if input_p.resolve() == output_p.resolve():
            raise ValueError('output file must differ from input file')
        report = normalize_file(input_p, output_p, target)
        reports.append(report)
        stderr_lines.extend((f'warning: {input_p}: {warning}' for warning in report.warnings))
        suffix = target_version_suffix(target)
        if suffix in {'V6', 'V7', 'V8'} and output_p.suffix.lower() == '.kicad_pcb':
            ensure_legacy_project_local_settings(_replace_extension(output_p, '.kicad_prl'), suffix, _replace_extension(input_p, '.kicad_prl'))
    if report_path:
        report_p = Path(report_path)
        report_p.parent.mkdir(parents=True, exist_ok=True)
        _write_text(report_p, format_reports_json(reports))
    changed = sum((1 for report in reports if report.changed))
    stdout = f'wrote {output_p}; normalized {changed} KiCad file(s)\n'
    stderr = '\n'.join(stderr_lines) + ('\n' if stderr_lines else '')
    return (stdout, stderr, 0)
