from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable


VERSION = "0.2.1"


@dataclass
class Node:
    atom: str | None = None
    quoted: bool = False
    children: list["Node"] = field(default_factory=list)

    @property
    def is_atom(self) -> bool:
        return self.atom is not None

    def head(self) -> str:
        return self.atom_at(0)

    def atom_at(self, index: int) -> str:
        if 0 <= index < len(self.children) and self.children[index].is_atom:
            return self.children[index].atom or ""
        return ""

    def set_atom_at(self, index: int, value: str, quoted: bool = False) -> bool:
        if 0 <= index < len(self.children) and self.children[index].is_atom:
            self.children[index].atom = value
            self.children[index].quoted = quoted
            return True
        return False

    def child_list(self, head: str) -> "Node | None":
        for child in self.children:
            if not child.is_atom and child.head() == head:
                return child
        return None


def atom(value: str, quoted: bool = False) -> Node:
    return Node(atom=value, quoted=quoted)


def sexpr_list(*children: Node) -> Node:
    return Node(children=list(children))


def _tokenize(text: str) -> list[tuple[str, bool]]:
    tokens: list[tuple[str, bool]] = []
    i = 0
    if text.startswith("\ufeff"):
        i = 1

    while i < len(text):
        ch = text[i]
        if ch.isspace():
            i += 1
            continue
        if ch in "()":
            tokens.append((ch, False))
            i += 1
            continue
        if ch == '"':
            i += 1
            value: list[str] = []
            while i < len(text):
                ch = text[i]
                i += 1
                if ch == '"':
                    tokens.append(("".join(value), True))
                    break
                if ch == "\\":
                    if i >= len(text):
                        raise ValueError("unterminated escape in quoted string")
                    escaped = text[i]
                    i += 1
                    value.append({"n": "\n", "t": "\t", '"': '"', "\\": "\\"}.get(escaped, escaped))
                else:
                    value.append(ch)
            else:
                raise ValueError("unterminated quoted string")
            continue

        start = i
        while i < len(text) and text[i] not in "()" and not text[i].isspace():
            i += 1
        tokens.append((text[start:i], False))

    return tokens


def _parse_list(tokens: list[tuple[str, bool]], pos: int) -> tuple[Node, int]:
    node = sexpr_list()
    while pos < len(tokens):
        text, quoted = tokens[pos]
        pos += 1
        if text == "(" and not quoted:
            child, pos = _parse_list(tokens, pos)
            node.children.append(child)
        elif text == ")" and not quoted:
            return node, pos
        else:
            node.children.append(atom(text, quoted))
    raise ValueError("unexpected end of input: unclosed '('")


def parse_sexpr(text: str) -> Node:
    tokens = _tokenize(text)
    if not tokens or tokens[0][0] != "(" or tokens[0][1]:
        raise ValueError("expected '('")
    root, pos = _parse_list(tokens, 1)
    if pos != len(tokens):
        raise ValueError("trailing tokens after root expression")
    return root


def _needs_quotes(value: str) -> bool:
    return not value or any(ch.isspace() or ch in '()"' for ch in value)


def _escape_atom(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t")


def _format_atom(node: Node) -> str:
    value = node.atom or ""
    if node.quoted or _needs_quotes(value):
        return f'"{_escape_atom(value)}"'
    return value


def _should_inline(node: Node) -> bool:
    if not node.children:
        return True
    total = 2
    for i, child in enumerate(node.children):
        if not child.is_atom:
            return False
        total += (1 if i else 0) + len(_format_atom(child))
    return total <= 88


def _write_node(node: Node, indent: int, out: list[str]) -> None:
    if node.is_atom:
        out.append(_format_atom(node))
        return
    out.append("(")
    if not node.children:
        out.append(")")
        return
    if _should_inline(node):
        for i, child in enumerate(node.children):
            if i:
                out.append(" ")
            _write_node(child, indent, out)
        out.append(")")
        return
    _write_node(node.children[0], indent + 2, out)
    for child in node.children[1:]:
        out.append("\n")
        out.append(" " * (indent + 2))
        _write_node(child, indent + 2, out)
    out.append(")")


def format_sexpr(root: Node) -> str:
    out: list[str] = []
    _write_node(root, 0, out)
    out.append("\n")
    return "".join(out)


@dataclass
class Document:
    path: Path
    root: Node
    kind: str
    version: str


@dataclass
class FileReport:
    path: str
    kind: str
    source_version: str
    target_version: str = ""
    changed: bool = False
    warnings: list[str] = field(default_factory=list)


def _is_number(value: str) -> bool:
    return bool(value) and value.isdigit()


def _is_int_atom(value: str) -> bool:
    if not value:
        return False
    if value[0] in "+-":
        return len(value) > 1 and value[1:].isdigit()
    return value.isdigit()


def _to_int(value: str, default: int = 0) -> int:
    try:
        return int(value)
    except ValueError:
        return default


def _bool_value(value: str, default: bool = True) -> bool:
    lower = value.lower()
    if lower in {"yes", "true", "1"}:
        return True
    if lower in {"no", "false", "0"}:
        return False
    return default


def detect_kind(path: Path, top_level: str) -> str:
    by_head = {
        "kicad_symbol_lib": "symbol-library",
        "kicad_sch": "schematic",
        "kicad_pcb": "board",
        "footprint": "footprint",
        "kicad_dru": "design-rules",
        "kicad_wks": "worksheet",
        "drawing_sheet": "worksheet",
    }
    if top_level in by_head:
        return by_head[top_level]
    return {
        ".kicad_sym": "symbol-library",
        ".kicad_sch": "schematic",
        ".kicad_pcb": "board",
        ".kicad_mod": "footprint",
        ".kicad_dru": "design-rules",
        ".kicad_wks": "worksheet",
    }.get(path.suffix.lower(), "unknown")


TARGET_VERSIONS: dict[str, dict[str, str]] = {
    "7.0": {"symbol-library": "20220914", "schematic": "20230121", "board": "20221018", "footprint": "20221018", "worksheet": "20220228", "design-rules": "20200610"},
    "8.0": {"symbol-library": "20231120", "schematic": "20231120", "board": "20240108", "footprint": "20240108", "worksheet": "20231118", "design-rules": "20200610"},
    "9.0": {"symbol-library": "20241209", "schematic": "20250114", "board": "20241229", "footprint": "20241229", "worksheet": "20231118", "design-rules": "20200610"},
    "10.0": {"symbol-library": "20251024", "schematic": "20260306", "board": "20260206", "footprint": "20260206", "worksheet": "20231118", "design-rules": "20200610"},
}


def _normalize_alias(target: str) -> str:
    value = target.strip().lower()
    if value.startswith("kicad-"):
        value = value[6:]
    if value.startswith("v"):
        value = value[1:]
    if "." not in value:
        value += ".0"
    return value


def resolve_target_version(kind: str, target: str) -> str:
    value = target.strip().lower()
    if not value:
        raise ValueError("empty target version")
    if _is_number(value):
        return value
    value = _normalize_alias(value)
    if value not in TARGET_VERSIONS:
        raise ValueError(f"unsupported KiCad target version alias: {target}")
    if kind not in TARGET_VERSIONS[value]:
        raise ValueError("target version is not defined for this file type")
    return TARGET_VERSIONS[value][kind]


def target_version_suffix(target: str) -> str:
    value = target.strip().lower()
    if value.startswith("kicad-"):
        value = value[6:]
    if value.startswith("v"):
        value = value[1:]
    for sep in ".-_":
        if sep in value:
            value = value.split(sep, 1)[0]
    return "V" + value.upper() if value else ""


def versioned_output_path(path: str | Path, target: str) -> Path:
    output = Path(path)
    label = target_version_suffix(target)
    if not label or output.stem.lower().endswith(("_" + label).lower()):
        return output
    return output.with_name(output.stem + "_" + label + output.suffix)


def load_document(path: Path) -> Document:
    root = parse_sexpr(path.read_text(encoding="utf-8-sig"))
    kind = detect_kind(path, root.head())
    version_node = root.child_list("version")
    return Document(path=path, root=root, kind=kind, version=version_node.atom_at(1) if version_node else "")


def ensure_version(doc: Document, version: str) -> None:
    version_node = doc.root.child_list("version")
    if version_node:
        if not version_node.set_atom_at(1, version):
            raise ValueError("document has an invalid top-level version field")
    else:
        doc.root.children.insert(1, sexpr_list(atom("version"), atom(version)))
    doc.version = version


FeatureRule = tuple[int, tuple[str, ...], str]


SYMBOL_RULES: tuple[FeatureRule, ...] = (
    (20220126, ("text_box", "textbox"), "symbol text boxes are not available"),
    (20240529, ("embedded_files", "embedded_file"), "embedded files are not available"),
    (20241209, ("private",), "private SCH_FIELD flags are not available"),
    (20250324, ("pin_group", "pin_groups"), "jumper pin groups are not available"),
    (20250829, ("rounded_rectangle", "roundrect"), "rounded rectangles are not available"),
    (20260508, ("ellipse", "ellipse_arc"), "native ellipse primitives are not available"),
)

SCHEMATIC_RULES: tuple[FeatureRule, ...] = (
    (20220126, ("text_box", "textbox"), "schematic text boxes are not available"),
    (20220622, ("simulation_model", "sim_model"), "new simulation model format is not available"),
    (20240101, ("table",), "schematic tables are not available"),
    (20240417, ("rule_area",), "schematic rule areas are not available"),
    (20240620, ("embedded_files", "embedded_file"), "embedded files are not available"),
    (20241209, ("private",), "private SCH_FIELD flags are not available"),
    (20250829, ("rounded_rectangle", "roundrect"), "rounded rectangles are not available"),
    (20250922, ("variants", "variant"), "schematic variants are not available"),
    (20260508, ("ellipse", "ellipse_arc"), "native ellipse primitives are not available"),
    (20260512, ("net_chain", "net_chains"), "schematic net chains are not available"),
)

BOARD_RULES: tuple[FeatureRule, ...] = (
    (20220131, ("gr_text_box", "fp_text_box", "text_box", "textbox"), "PCB textboxes are not available"),
    (20220621, ("image",), "PCB image objects are not available"),
    (20220818, ("net_tie", "net_ties"), "first-class net-tie storage is not available"),
    (20231007, ("generated",), "PCB generative objects are not available"),
    (20240108, ("teardrop", "teardrops"), "teardrop parameters are not available"),
    (20240202, ("table",), "PCB tables are not available"),
    (20240609, ("tenting",), "tenting keyword is not available"),
    (20240706, ("embedded_files", "embedded_file", "embedded_fonts"), "embedded files are not available"),
    (20240928, ("component_class", "component_classes"), "component classes are not available"),
    (20240929, ("padstack",), "complex padstacks are not available"),
    (20241006, ("via_stack", "viastack"), "via stacks are not available"),
    (20241009, ("rule_area",), "placement/rule areas are not available"),
    (20250228, ("via_protection", "covering", "plugging", "filling", "capping"), "IPC-4761 via protection is not available"),
    (20250818, ("custom_layer_count", "custom_layer_counts"), "custom footprint layer counts are not available"),
    (20250829, ("rounded_rectangle", "roundrect"), "rounded rectangles are not available"),
    (20250901, ("point",), "PCB point objects are not available"),
    (20250914, ("barcode", "pcb_barcode", "gr_barcode", "fp_barcode"), "PCB barcode objects are not available"),
    (20251101, ("backdrill", "tertiary_drill", "front_post_machining", "back_post_machining"), "backdrill and tertiary drill fields are not available"),
    (20260101, ("variants", "variant"), "PCB variants are not available"),
    (20260410, ("extruded",), "extruded footprint 3D body models are not available"),
    (20260508, ("gr_ellipse", "gr_ellipse_arc", "fp_ellipse", "fp_ellipse_arc"), "native PCB ellipse primitives are not available"),
    (20260511, ("spec_frequency", "dielectric_model"), "dielectric frequency-dependent stackup fields are not available"),
    (20260512, ("net_chains", "net_chain"), "PCB net chains are not available"),
    (20260513, ("thieving",), "copper thieving zone fill mode is not available"),
)


def _walk(node: Node) -> Iterable[Node]:
    if node.is_atom:
        return
    yield node
    for child in node.children:
        if not child.is_atom:
            yield from _walk(child)


def remove_descendants_by_head(root: Node, heads: set[str]) -> int:
    if root.is_atom:
        return 0
    removed = 0
    kept: list[Node] = []
    for child in root.children:
        if not child.is_atom and child.head() in heads:
            removed += 1
            continue
        if not child.is_atom:
            removed += remove_descendants_by_head(child, heads)
        kept.append(child)
    root.children = kept
    return removed


def remove_children_from_parents(root: Node, parents: set[str], children: set[str]) -> int:
    removed = 0
    for node in _walk(root):
        if node.head() in parents:
            before = len(node.children)
            node.children = [c for c in node.children if c.is_atom or c.head() not in children]
            removed += before - len(node.children)
    return removed


def remove_direct_children_by_head(root: Node, head: str) -> int:
    before = len(root.children)
    root.children = [c for c in root.children if c.is_atom or c.head() != head]
    return before - len(root.children)


def rename_child_head_in_parents(root: Node, parents: set[str], old: str, new: str) -> int:
    changed = 0
    for node in _walk(root):
        if node.head() in parents:
            for child in node.children:
                if not child.is_atom and child.head() == old and child.set_atom_at(0, new):
                    changed += 1
    return changed


def remove_atoms_from_headed_lists(root: Node, parents: set[str], atoms: set[str]) -> int:
    removed = 0
    for node in _walk(root):
        if node.head() in parents:
            kept = [node.children[0]]
            for child in node.children[1:]:
                if child.is_atom and child.atom in atoms:
                    removed += 1
                else:
                    kept.append(child)
            node.children = kept
    return removed


def flatten_child_lists_to_atoms_in_parents(root: Node, parents: set[str], children: set[str]) -> int:
    changed = 0
    for node in _walk(root):
        if node.head() in parents:
            for i, child in enumerate(node.children):
                if not child.is_atom and child.head() in children:
                    node.children[i] = atom(child.head())
                    changed += 1
    return changed


def downgrade_bool_lists_to_atoms(root: Node, heads: set[str]) -> int:
    changed = 0
    for node in list(_walk(root)):
        kept: list[Node] = []
        for child in node.children:
            if not child.is_atom and child.head() in heads:
                if _bool_value(child.atom_at(1), True):
                    kept.append(atom(child.head()))
                changed += 1
            else:
                kept.append(child)
        node.children = kept
    return changed


def downgrade_boolean_presence_nodes(root: Node, heads: set[str]) -> int:
    changed = 0
    for node in list(_walk(root)):
        kept: list[Node] = []
        for child in node.children:
            if not child.is_atom and child.head() in heads and len(child.children) > 1:
                value = child.atom_at(1).lower()
                if value in {"yes", "true", "1"}:
                    child.children = child.children[:1]
                    kept.append(child)
                    changed += 1
                    continue
                if value in {"no", "false", "0"}:
                    changed += 1
                    continue
            kept.append(child)
        node.children = kept
    return changed


def downgrade_font_style_lists_to_atoms(root: Node) -> int:
    changed = 0
    for node in _walk(root):
        if node.head() != "font":
            continue
        kept: list[Node] = []
        for child in node.children:
            if not child.is_atom and child.head() in {"bold", "italic"} and len(child.children) > 1:
                if _bool_value(child.atom_at(1), True):
                    kept.append(atom(child.head()))
                changed += 1
            else:
                kept.append(child)
        node.children = kept
    return changed


def ensure_legacy_property_ids(root: Node) -> int:
    standard = {"Reference", "Value", "Footprint", "Datasheet", "ki_keywords", "ki_fp_filters"}
    changed = 0
    for node in _walk(root):
        if node.head() not in {"symbol", "sheet"}:
            continue
        next_id = 5
        for child in node.children:
            if child.is_atom or child.head() != "property":
                continue
            if child.atom_at(1) in standard or child.child_list("id"):
                continue
            child.children.insert(min(3, len(child.children)), sexpr_list(atom("id"), atom(str(next_id))))
            next_id += 1
            changed += 1
    return changed


def move_property_hide_to_effects(root: Node) -> int:
    changed = 0
    for node in _walk(root):
        if node.head() != "property":
            continue
        hidden = False
        kept: list[Node] = []
        for child in node.children:
            if child.is_atom and child.atom == "hide":
                hidden = True
                changed += 1
            elif not child.is_atom and child.head() == "hide":
                hidden = _bool_value(child.atom_at(1), True)
                changed += 1
            else:
                kept.append(child)
        node.children = kept
        effects = node.child_list("effects")
        if hidden and effects and not effects.child_list("hide"):
            effects.children.append(atom("hide"))
            changed += 1
    return changed


def downgrade_tenting_to_legacy_atoms(root: Node) -> int:
    changed = 0
    for node in _walk(root):
        if node.head() != "tenting":
            continue
        front_node = node.child_list("front")
        back_node = node.child_list("back")
        if not front_node and not back_node:
            continue
        children = [atom("tenting")]
        if front_node and _bool_value(front_node.atom_at(1), True):
            children.append(atom("front"))
        if back_node and _bool_value(back_node.atom_at(1), True):
            children.append(atom("back"))
        if len(children) == 1:
            children.append(atom("none"))
        node.children = children
        changed += 1
    return changed


def _property_node(name: str, value: str) -> Node:
    return sexpr_list(atom("property"), atom(name, True), atom(value, True))


def downgrade_pcb_footprint_fields(root: Node) -> int:
    changed = 0
    for node in list(_walk(root)):
        if node.head() not in {"footprint", "module"}:
            continue
        kept: list[Node] = []
        for child in node.children:
            if child.is_atom:
                kept.append(child)
                continue
            if child.head() == "property":
                name = child.atom_at(1)
                if name in {"Reference", "Value"}:
                    kind = "reference" if name == "Reference" else "value"
                    text = sexpr_list(atom("fp_text"), atom(kind), atom(child.atom_at(2), True))
                    for sub in child.children[3:]:
                        if not sub.is_atom and sub.head() == "hide":
                            if _bool_value(sub.atom_at(1), True):
                                text.children.append(atom("hide"))
                        else:
                            text.children.append(sub)
                    kept.append(text)
                    changed += 1
                    continue
                if name == "Description" and child.set_atom_at(1, "ki_description", True):
                    changed += 1
                if len(child.children) > 3:
                    child.children = child.children[:3]
                    changed += 1
            elif child.head() == "sheetname":
                if child.atom_at(1):
                    kept.append(_property_node("Sheetname", child.atom_at(1)))
                    changed += 1
                continue
            elif child.head() == "sheetfile":
                if child.atom_at(1):
                    kept.append(_property_node("Sheetfile", child.atom_at(1)))
                    changed += 1
                continue
            kept.append(child)
        node.children = kept
    return changed


def downgrade_user_layer_types(root: Node) -> int:
    changed = 0
    for node in _walk(root):
        if node.head() == "layers":
            for layer in node.children:
                if not layer.is_atom and len(layer.children) >= 4:
                    if layer.atom_at(1).startswith("User.") and layer.atom_at(2) in {"front", "back", "auxiliary"}:
                        layer.set_atom_at(2, "user")
                        changed += 1
    return changed


def downgrade_pcbplotparams_bools(root: Node) -> int:
    changed = 0
    for node in _walk(root):
        if node.head() == "pcbplotparams":
            for child in node.children:
                if not child.is_atom and len(child.children) > 1:
                    value = child.atom_at(1).lower()
                    if value == "yes" and child.set_atom_at(1, "true"):
                        changed += 1
                    elif value == "no" and child.set_atom_at(1, "false"):
                        changed += 1
    return changed


def downgrade_shape_fill_no_to_none(root: Node) -> int:
    heads = {"gr_rect", "gr_circle", "gr_poly", "fp_rect", "fp_circle", "fp_poly"}
    changed = 0
    for node in _walk(root):
        if node.head() in heads:
            fill = node.child_list("fill")
            if fill and fill.atom_at(1).lower() == "no" and fill.set_atom_at(1, "none"):
                changed += 1
    return changed


def downgrade_shape_hatch_fills(root: Node) -> int:
    heads = {"gr_rect", "gr_circle", "gr_poly", "fp_rect", "fp_circle", "fp_poly"}
    changed = 0
    for node in _walk(root):
        if node.head() in heads:
            fill = node.child_list("fill")
            if fill and fill.atom_at(1) in {"hatch", "reverse_hatch", "cross_hatch"}:
                fill.set_atom_at(1, "yes")
                changed += 1
    return changed


def ensure_zone_filled_areas_thickness(root: Node) -> int:
    changed = 0
    for node in _walk(root):
        if node.head() == "zone" and node.child_list("filled_polygon") and not node.child_list("filled_areas_thickness"):
            insert_at = len(node.children)
            for i, child in enumerate(node.children[1:], 1):
                if not child.is_atom and child.head() == "fill":
                    insert_at = i
                    break
            node.children.insert(insert_at, sexpr_list(atom("filled_areas_thickness"), atom("no")))
            changed += 1
    return changed


def remove_nodes_containing_child(root: Node, parent_head: str, child_head: str) -> int:
    removed = 0
    for node in list(_walk(root)):
        kept: list[Node] = []
        for child in node.children:
            if not child.is_atom and child.head() == parent_head and child.child_list(child_head):
                removed += 1
            else:
                kept.append(child)
        node.children = kept
    return removed


def replace_atom_values_in_parents(root: Node, parents: set[str], old: str, new: str) -> int:
    changed = 0
    for node in _walk(root):
        if node.head() in parents:
            for child in node.children:
                if child.is_atom and child.atom == old:
                    child.atom = new
                    changed += 1
    return changed


def downgrade_dimensions_to_text(root: Node) -> int:
    def convert(node: Node, inside_footprint: bool) -> int:
        inside = inside_footprint or node.head() in {"footprint", "module"}
        changed = 0
        kept: list[Node] = []
        for child in node.children:
            if not child.is_atom and child.head() == "dimension":
                source = child.child_list("gr_text")
                if source:
                    text = sexpr_list(atom("fp_text" if inside else "gr_text"))
                    if inside:
                        text.children.extend([atom("user"), atom(source.atom_at(1), True)])
                    else:
                        text.children.append(atom(source.atom_at(1), True))
                    text.children.extend(source.children[2:])
                    kept.append(text)
                changed += 1
            else:
                if not child.is_atom:
                    changed += convert(child, inside)
                kept.append(child)
        node.children = kept
        return changed
    return convert(root, False)


def downgrade_board_net_names_to_codes(root: Node) -> int:
    codes: dict[str, int] = {"": 0}
    next_code = 1

    def add_name(name: str) -> None:
        nonlocal next_code
        if name not in codes:
            codes[name] = next_code
            next_code += 1

    for child in root.children:
        if not child.is_atom and child.head() == "net":
            if _is_int_atom(child.atom_at(1)):
                code = _to_int(child.atom_at(1))
                name = child.atom_at(2)
                codes.setdefault(name, code)
                next_code = max(next_code, code + 1)
            else:
                add_name(child.atom_at(1))

    for node in _walk(root):
        if node.head() == "net" and not _is_int_atom(node.atom_at(1)):
            add_name(node.atom_at(1))

    changed = 0

    def rewrite(node: Node, parent: str = "") -> None:
        nonlocal changed
        if node.head() == "net" and not _is_int_atom(node.atom_at(1)):
            name = node.atom_at(1)
            new_children = [node.children[0], atom(str(codes.get(name, 0)))]
            if parent in {"kicad_pcb", "pad"}:
                new_children.extend(node.children[1:])
            node.children = new_children
            changed += 1
        if node.head() == "zone":
            net = node.child_list("net")
            if net and not _is_int_atom(net.atom_at(1)) and not node.child_list("net_name"):
                node.children.append(sexpr_list(atom("net_name"), atom(net.atom_at(1), True)))
                changed += 1
        head = node.head()
        for child in node.children:
            if not child.is_atom:
                rewrite(child, head)

    rewrite(root)

    existing_codes = {
        _to_int(c.atom_at(1))
        for c in root.children
        if not c.is_atom and c.head() == "net" and _is_int_atom(c.atom_at(1))
    }
    new_entries = sorted(((name, code) for name, code in codes.items() if code not in existing_codes), key=lambda item: (item[1], item[0]))
    if new_entries and root.head() == "kicad_pcb":
        last_net = -1
        item_heads = {
            "arc", "dimension", "footprint", "gr_arc", "gr_circle", "gr_curve",
            "gr_line", "gr_poly", "gr_rect", "gr_text", "group", "image",
            "segment", "via", "zone",
        }
        first_item = len(root.children)

        for i, child in enumerate(root.children):
            if not child.is_atom and child.head() == "net":
                last_net = i
            elif not child.is_atom and child.head() in item_heads and first_item == len(root.children):
                first_item = i

        # Legacy net declarations must stay after setup metadata and before board items.
        insert_at = last_net + 1 if last_net >= 0 else first_item

        for offset, (name, code) in enumerate(new_entries):
            root.children.insert(insert_at + offset, sexpr_list(atom("net"), atom(str(code)), atom(name, True)))
        changed += len(new_entries)

    return changed


def remove_introduced(root: Node, target: int, rules: Iterable[FeatureRule]) -> list[str]:
    warnings: list[str] = []
    for min_version, heads, reason in rules:
        if target >= min_version:
            continue
        removed = remove_descendants_by_head(root, set(heads))
        if removed:
            warnings.append(f"removed {removed} node(s) introduced in {min_version}: {reason}")
    return warnings


def _warn_if_changed(warnings: list[str], count: int, message: str) -> None:
    if count > 0:
        warnings.append(message)


def _apply_when(warnings: list[str], condition: bool, rewrite: Callable[[], int], message: str) -> None:
    if condition:
        _warn_if_changed(warnings, rewrite(), message)


def apply_downgrade_rules(doc: Document, target: int) -> list[str]:
    root = doc.root
    warnings: list[str] = []

    if doc.kind == "symbol-library":
        warnings.extend(remove_introduced(root, target, SYMBOL_RULES))
        _apply_when(warnings, target < 20231120, lambda: remove_direct_children_by_head(root, "generator_version"), "removed symbol library generator_version fields")
        _apply_when(warnings, target < 20241209, lambda: remove_descendants_by_head(root, {"embedded_fonts"}), "removed symbol library embedded_fonts fields")
        _apply_when(warnings, target < 20240108, lambda: downgrade_font_style_lists_to_atoms(root), "downgraded symbol library font bold/italic bool fields")
        _apply_when(warnings, target <= 20241209, lambda: remove_children_from_parents(root, {"font"}, {"face"}), "removed symbol library font face fields")
        if target < 20241004:
            _warn_if_changed(warnings, downgrade_bool_lists_to_atoms(root, {"hide"}), "downgraded symbol library boolean hide fields")
            _warn_if_changed(warnings, flatten_child_lists_to_atoms_in_parents(root, {"pin_names", "pin_numbers"}, {"hide"}), "downgraded symbol pin visibility fields")
        if target < 20241209:
            _warn_if_changed(warnings, ensure_legacy_property_ids(root), "added legacy symbol property ids")
            _warn_if_changed(warnings, move_property_hide_to_effects(root), "moved symbol property hide flags to effects")
        _apply_when(warnings, target < 20251024, lambda: remove_children_from_parents(root, {"symbol"}, {"in_pos_files"}), "removed symbol library position file flags")
        _apply_when(warnings, target < 20250324, lambda: remove_children_from_parents(root, {"symbol"}, {"duplicate_pin_numbers_are_jumpers"}), "removed symbol library jumper pin-number flags")
        _apply_when(warnings, target < 20250227, lambda: remove_children_from_parents(root, {"symbol"}, {"power"}), "removed symbol library power class flags")
        _apply_when(warnings, target < 20251024, lambda: remove_children_from_parents(root, {"property"}, {"show_name", "do_not_autoplace"}), "removed symbol property formatting fields")

    elif doc.kind == "schematic":
        warnings.extend(remove_introduced(root, target, SCHEMATIC_RULES))
        _apply_when(warnings, target < 20231120, lambda: remove_direct_children_by_head(root, "generator_version"), "removed schematic generator_version fields")
        _apply_when(warnings, target < 20260326, lambda: remove_descendants_by_head(root, {"locked"}), "removed schematic locked fields introduced after target version")
        _apply_when(warnings, target < 20260306, lambda: remove_descendants_by_head(root, {"embedded_fonts"}), "removed schematic embedded_fonts fields")
        _apply_when(warnings, target < 20250827, lambda: remove_descendants_by_head(root, {"body_styles", "body_style"}), "removed schematic custom body style fields")
        _apply_when(warnings, target < 20250114, lambda: remove_children_from_parents(root, {"text", "text_box", "textbox"}, {"exclude_from_sim"}), "removed schematic text simulation flags")
        _apply_when(warnings, target < 20260306, lambda: remove_children_from_parents(root, {"sheet"}, {"exclude_from_sim", "in_bom", "on_board", "dnp"}), "removed schematic sheet assembly/simulation flags")
        _apply_when(warnings, target <= 20230121, lambda: remove_descendants_by_head(root, {"exclude_from_sim"}), "removed schematic simulation exclusion flags")
        _apply_when(warnings, target < 20251024, lambda: remove_children_from_parents(root, {"symbol"}, {"in_pos_files"}), "removed schematic symbol position file flags")
        _apply_when(warnings, target < 20250324, lambda: remove_children_from_parents(root, {"symbol"}, {"duplicate_pin_numbers_are_jumpers"}), "removed schematic library symbol jumper pin-number flags")
        _apply_when(warnings, target < 20250227, lambda: remove_children_from_parents(root, {"symbol"}, {"power"}), "removed schematic library symbol power class flags")
        if target < 20241004:
            _warn_if_changed(warnings, downgrade_bool_lists_to_atoms(root, {"hide"}), "downgraded schematic boolean hide fields")
            _warn_if_changed(warnings, flatten_child_lists_to_atoms_in_parents(root, {"pin_names", "pin_numbers"}, {"hide"}), "downgraded schematic symbol pin visibility fields")
        _apply_when(warnings, target < 20240108, lambda: downgrade_font_style_lists_to_atoms(root), "downgraded schematic font bold/italic bool fields")
        _apply_when(warnings, target <= 20250114, lambda: remove_children_from_parents(root, {"font"}, {"face"}), "removed schematic font face fields")
        if target < 20241209:
            _warn_if_changed(warnings, ensure_legacy_property_ids(root), "added legacy schematic property ids")
            _warn_if_changed(warnings, move_property_hide_to_effects(root), "moved schematic property hide flags to effects")
        _apply_when(warnings, target < 20231120, lambda: remove_children_from_parents(root, {"symbol", "sheet"}, {"fields_autoplaced"}), "removed schematic symbol/sheet fields_autoplaced fields")
        _apply_when(warnings, target < 20251028, lambda: remove_children_from_parents(root, {"property"}, {"show_name", "do_not_autoplace"}), "removed schematic property formatting fields")
        _apply_when(warnings, target < 20260306, lambda: remove_direct_children_by_head(root, "group"), "removed schematic group nodes")

    elif doc.kind in {"board", "footprint"}:
        warnings.extend(remove_introduced(root, target, BOARD_RULES))
        _apply_when(warnings, target < 20260410, lambda: remove_nodes_containing_child(root, "model", "type"), "removed typed/extruded 3D model blocks")
        _apply_when(warnings, target < 20260513, lambda: replace_atom_values_in_parents(root, {"mode"}, "thieving", "polygon"), "downgraded copper thieving fill modes to polygon fill")
        _apply_when(warnings, target >= 20220225, lambda: remove_children_from_parents(root, {"footprint", "module"}, {"tedit"}), "removed obsolete footprint tedit fields")
        _apply_when(warnings, target >= 20200628, lambda: remove_children_from_parents(root, {"setup"}, {"visible_elements"}), "removed obsolete board visible_elements settings")
        _apply_when(warnings, target < 20240703, lambda: downgrade_user_layer_types(root), "removed user-layer type qualifiers")
        if target < 20241010:
            _warn_if_changed(warnings, remove_children_from_parents(root, {"gr_line", "gr_arc", "gr_circle", "gr_rect", "gr_poly", "fp_line", "fp_arc", "fp_circle", "fp_rect", "fp_poly"}, {"solder_mask_margin"}), "removed graphic solder_mask_margin fields")
        if target < 20241030:
            _warn_if_changed(warnings, downgrade_bool_lists_to_atoms(root, {"suppress_zeroes", "keep_text_aligned"}), "downgraded dimension boolean fields to legacy atom syntax")
            _warn_if_changed(warnings, remove_children_from_parents(root, {"style"}, {"arrow_direction"}), "removed dimension arrow direction fields")
        _apply_when(warnings, target < 20241009, lambda: remove_children_from_parents(root, {"zone"}, {"placement"}), "removed zone placement fields")
        _apply_when(warnings, target < 20241007, lambda: remove_children_from_parents(root, {"segment", "arc"}, {"solder_mask_margin", "solder_mask_layer"}), "removed track soldermask layer/margin fields")
        _apply_when(warnings, target < 20240617, lambda: remove_children_from_parents(root, {"table_cell"}, {"angle"}), "removed PCB table cell angle fields")
        if target < 20250228:
            _warn_if_changed(warnings, downgrade_tenting_to_legacy_atoms(root), "downgraded tenting front/back bool lists to legacy atom syntax")
            _warn_if_changed(warnings, remove_descendants_by_head(root, {"covering", "plugging", "filling", "capping"}), "removed IPC-4761 via protection fields")
        if target < 20231212:
            _warn_if_changed(warnings, downgrade_boolean_presence_nodes(root, {"locked", "hide"}), "downgraded board/footprint boolean locked/hide fields")
            _warn_if_changed(warnings, remove_descendants_by_head(root, {"unlocked"}), "removed PCB text keep-upright unlock fields")
            _warn_if_changed(warnings, remove_children_from_parents(root, {"model"}, {"hide"}), "removed legacy-incompatible 3D model hide fields")
        _apply_when(warnings, target < 20231014, lambda: remove_direct_children_by_head(root, "generator_version"), "removed board/footprint generator_version fields")
        if target < 20230924:
            _warn_if_changed(warnings, downgrade_pcbplotparams_bools(root), "downgraded pcbplotparams boolean values")
            _warn_if_changed(warnings, downgrade_shape_fill_no_to_none(root), "downgraded PCB shape fill no values to none")
        if target < 20230730:
            _warn_if_changed(warnings, remove_children_from_parents(root, {"gr_line", "gr_arc", "gr_circle", "gr_rect", "gr_poly", "gr_curve", "fp_line", "fp_arc", "fp_circle", "fp_rect", "fp_poly", "fp_curve"}, {"net"}), "removed PCB graphic shape net connectivity fields")
        if target < 20240108:
            _warn_if_changed(warnings, remove_children_from_parents(root, {"group"}, {"locked"}), "removed group locked fields")
            _warn_if_changed(warnings, downgrade_font_style_lists_to_atoms(root), "downgraded PCB font bold/italic bool fields")
        _apply_when(warnings, target < 20230620, lambda: downgrade_pcb_footprint_fields(root), "downgraded PCB footprint fields to legacy storage")
        if target < 20231231:
            parents = {"footprint", "module", "pad", "via", "segment", "arc", "zone", "gr_line", "gr_arc", "gr_circle", "gr_rect", "gr_poly", "gr_curve", "gr_text", "fp_line", "fp_arc", "fp_circle", "fp_rect", "fp_poly", "fp_curve", "fp_text"}
            _warn_if_changed(warnings, rename_child_head_in_parents(root, parents, "uuid", "tstamp"), "renamed footprint uuid fields back to legacy tstamp")
            _warn_if_changed(warnings, rename_child_head_in_parents(root, {"group", "generated"}, "uuid", "id"), "renamed board group/generated uuid fields back to id")
        _apply_when(warnings, target < 20250324, lambda: remove_children_from_parents(root, {"footprint"}, {"duplicate_pad_numbers_are_jumpers", "jumper_pad_groups"}), "removed footprint jumper pad fields")
        _apply_when(warnings, target <= 20221018, lambda: remove_atoms_from_headed_lists(root, {"attr"}, {"dnp"}), "removed footprint dnp attributes")
        _apply_when(warnings, target < 20250309, lambda: remove_children_from_parents(root, {"placement"}, {"component_class"}), "removed rule_area component_class placement sources")
        _apply_when(warnings, target < 20250222, lambda: downgrade_shape_hatch_fills(root), "downgraded PCB shape hatch fills")
        _apply_when(warnings, target < 20250210, lambda: remove_children_from_parents(root, {"gr_text_box", "fp_text_box"}, {"knockout"}), "removed PCB text box knockout fields")
        _apply_when(warnings, target < 20250210, lambda: ensure_zone_filled_areas_thickness(root), "tagged cached zone fills as polygon fills")
        _apply_when(warnings, target <= 20241229, lambda: remove_children_from_parents(root, {"font"}, {"face"}), "removed PCB font face fields")
        if target <= 20221018:
            _warn_if_changed(warnings, remove_children_from_parents(root, {"pad", "via"}, {"remove_unused_layers"}), "removed pad/via remove_unused_layers fields")
            _warn_if_changed(warnings, downgrade_dimensions_to_text(root), "downgraded PCB dimensions to legacy text annotations")
            _warn_if_changed(warnings, remove_descendants_by_head(root, {"locked"}), "removed legacy-incompatible locked fields")
            _warn_if_changed(warnings, downgrade_boolean_presence_nodes(root, {"free"}), "downgraded free via fields")
        _apply_when(warnings, target < 20251101, lambda: remove_children_from_parents(root, {"pad", "via"}, {"front_post_machining", "back_post_machining"}), "removed pad/via post-machining fields")
        _apply_when(warnings, target < 20251028, lambda: downgrade_board_net_names_to_codes(root), "added legacy netcodes to board net references")

    elif doc.kind == "worksheet" and target < 20220228:
        warnings.extend(remove_introduced(root, target, ((20220228, ("font",), "worksheet font blocks are not available"),)))

    return warnings


def is_kicad_document_path(path: Path) -> bool:
    return path.suffix.lower() in {".kicad_sch", ".kicad_pcb", ".kicad_sym", ".kicad_mod", ".kicad_dru", ".kicad_wks"}


def is_kicad_project_file_path(path: Path) -> bool:
    name = path.name.lower()
    ext = path.suffix.lower()
    if not name or name.startswith(".#") or name.endswith("~"):
        return False
    if ext in {".bak", ".backup", ".bck", ".orig", ".tmp", ".temp"}:
        return False
    return (
        name in {"fp-lib-table", "sym-lib-table"}
        or ext in {".kicad_pro", ".kicad_prl", ".step", ".stp", ".wrl", ".iges", ".igs", ".stl", ".obj"}
        or is_kicad_document_path(path)
    )


def is_excluded_project_dir_name(name: str) -> bool:
    value = name.lower()
    excluded = {".git", ".svn", ".hg", ".history", ".backup", "__pycache__", "history", "histories", "backup", "backups", "archive", "archives", "old", "gerber", "gerbers", "gerberfiles", "gerber_files", "fab", "fabrication", "outputs", "production", "plot", "plots", "export", "exports", "bom", "ibom", "assembly", "jlcpcb", "oshpark"}
    return value in excluded or "backup" in value or "history" in value or "gerber" in value


def copy_project_tree(input_path: Path, output_path: Path) -> list[Path]:
    src = input_path.resolve()
    dest = output_path.resolve()
    if src == dest:
        raise ValueError("output directory must differ from input directory")
    copied: list[Path] = []
    for path in src.rglob("*"):
        rel = path.relative_to(src)
        if any(is_excluded_project_dir_name(part) for part in rel.parts[:-1]):
            continue
        if path.is_dir():
            continue
        if not path.is_file() or not is_kicad_project_file_path(path):
            continue
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, out)
        copied.append(out)
    return copied


def normalize_file(input_path: Path, output_path: Path, target: str) -> FileReport:
    doc = load_document(input_path)
    report = FileReport(str(output_path), doc.kind, doc.version)
    resolved = resolve_target_version(doc.kind, target)
    source = int(doc.version) if _is_number(doc.version) else 0
    target_int = int(resolved)
    if source and source < target_int:
        if input_path.resolve() != output_path.resolve():
            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(input_path, output_path)
        report.target_version = doc.version
        return report
    report.warnings = apply_downgrade_rules(doc, target_int)
    ensure_version(doc, resolved)
    report.target_version = doc.version
    report.changed = True
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as out:
        out.write(format_sexpr(doc.root))
    return report


def ensure_legacy_project_local_settings(path: Path, suffix: str) -> None:
    meta_version = 3 if suffix == "V8" else 4
    visible_items = [0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 15, 16, 17, 18, 19, 20, 21, 23, 24, 25, 26, 27, 28, 29, 30, 32, 33, 34, 35, 36, 39, 40, 41]
    payload = {
        "board": {"visible_items": visible_items, "visible_layers": "ffffffff_ffffffff_ffffffff_ffffffff"},
        "meta": {"filename": path.name, "version": meta_version},
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _replace_extension(path: Path, suffix: str) -> Path:
    return path.with_suffix(suffix)


def format_reports_json(reports: list[FileReport]) -> str:
    data = {
        "files": [
            {
                "path": r.path,
                "kind": r.kind,
                "source_version": r.source_version,
                **({"target_version": r.target_version} if r.target_version else {}),
                "changed": r.changed,
                **({"warnings": r.warnings} if r.warnings else {}),
            }
            for r in reports
        ]
    }
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def convert(input_path: str | Path, output_path: str | Path, target: str, report_path: str | Path | None = None) -> tuple[str, str, int]:
    input_p = Path(input_path)
    output_p = versioned_output_path(output_path, target)
    reports: list[FileReport] = []
    stderr_lines: list[str] = []

    if input_p.is_dir() or input_p.suffix.lower() == ".kicad_pro":
        src_dir = input_p if input_p.is_dir() else input_p.parent
        copied = copy_project_tree(src_dir, output_p)
        for path in copied:
            if is_kicad_document_path(path):
                report = normalize_file(path, path, target)
                reports.append(report)
                stderr_lines.extend(f"warning: {path}: {warning}" for warning in report.warnings)
        suffix = target_version_suffix(target)
        if suffix in {"V7", "V8"}:
            for path in copied:
                if path.suffix.lower() == ".kicad_pcb":
                    ensure_legacy_project_local_settings(_replace_extension(path, ".kicad_prl"), suffix)
    else:
        if input_p.resolve() == output_p.resolve():
            raise ValueError("output file must differ from input file")
        report = normalize_file(input_p, output_p, target)
        reports.append(report)
        stderr_lines.extend(f"warning: {input_p}: {warning}" for warning in report.warnings)
        suffix = target_version_suffix(target)
        if suffix in {"V7", "V8"} and output_p.suffix.lower() == ".kicad_pcb":
            ensure_legacy_project_local_settings(_replace_extension(output_p, ".kicad_prl"), suffix)

    if report_path:
        Path(report_path).write_text(format_reports_json(reports), encoding="utf-8")

    changed = sum(1 for report in reports if report.changed)
    stdout = f"wrote {output_p}; normalized {changed} KiCad file(s)\n"
    stderr = "\n".join(stderr_lines) + ("\n" if stderr_lines else "")
    return stdout, stderr, 0
