from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Optional


VERSION = "0.2.1"
ESCAPES = {"n": "\n", "t": "\t", '"': '"', "\\": "\\"}


class Node:
    __slots__ = ("atom", "quoted", "children")

    def __init__(
        self,
        atom: str | None = None,
        quoted: bool = False,
        children: list["Node"] | None = None,
    ) -> None:
        self.atom = atom
        self.quoted = quoted
        self.children = [] if children is None else children

    @property
    def is_atom(self) -> bool:
        return self.atom is not None

    def head(self) -> str:
        children = self.children
        if children:
            value = children[0].atom
            if value is not None:
                return value
        return ""

    def atom_at(self, index: int) -> str:
        children = self.children
        if 0 <= index < len(children):
            value = children[index].atom
            if value is not None:
                return value
        return ""

    def set_atom_at(self, index: int, value: str, quoted: bool = False) -> bool:
        children = self.children
        if 0 <= index < len(children) and children[index].atom is not None:
            children[index].atom = value
            children[index].quoted = quoted
            return True
        return False

    def child_list(self, head: str) -> "Node | None":
        for child in self.children:
            if child.atom is None and child.head() == head:
                return child
        return None


def atom(value: str, quoted: bool = False) -> Node:
    return Node(value, quoted)


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
                    value.append(ESCAPES.get(escaped, escaped))
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
    root: Node | None = None
    stack: list[Node] = []
    i = 1 if text.startswith("\ufeff") else 0
    n = len(text)

    while i < n:
        ch = text[i]
        if ch <= " " or (ch > "\x7f" and ch.isspace()):
            i += 1
            continue
        if root is not None and not stack:
            raise ValueError("trailing tokens after root expression")

        if ch == "(":
            node = Node()
            if stack:
                stack[-1].children.append(node)
            elif root is None:
                root = node
            else:
                raise ValueError("trailing tokens after root expression")
            stack.append(node)
            i += 1
            continue

        if ch == ")":
            if not stack:
                raise ValueError("unexpected ')'")
            stack.pop()
            i += 1
            continue

        if not stack:
            raise ValueError("expected '('")

        if ch == '"':
            i += 1
            value: list[str] = []
            while i < n:
                ch = text[i]
                i += 1
                if ch == '"':
                    stack[-1].children.append(Node(atom="".join(value), quoted=True))
                    break
                if ch == "\\":
                    if i >= n:
                        raise ValueError("unterminated escape in quoted string")
                    escaped = text[i]
                    i += 1
                    value.append(ESCAPES.get(escaped, escaped))
                else:
                    value.append(ch)
            else:
                raise ValueError("unterminated quoted string")
            continue

        start = i
        while i < n:
            ch = text[i]
            if ch in "()" or ch <= " " or (ch > "\x7f" and ch.isspace()):
                break
            i += 1
        stack[-1].children.append(Node(atom=text[start:i]))

    if root is None:
        raise ValueError("expected '('")
    if stack:
        raise ValueError("unexpected end of input: unclosed '('")
    return root


def _needs_quotes(value: str) -> bool:
    if not value:
        return True
    for ch in value:
        if ch in '()"' or ch <= " " or (ch > "\x7f" and ch.isspace()):
            return True
    return False


def _escape_atom(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t")


def _format_atom(node: Node, cache: dict[tuple[str, bool], str] | None = None) -> str:
    value = node.atom or ""
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
        cache[(value, quoted)] = formatted
    return formatted


def _inline_parts(node: Node, cache: dict[tuple[str, bool], str]) -> list[str] | None:
    children = node.children
    if not children:
        return []
    parts: list[str] = []
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


def _write_node(node: Node, indent: int, out: list[str], cache: dict[tuple[str, bool], str]) -> None:
    if node.atom is not None:
        out.append(_format_atom(node, cache))
        return
    out.append("(")
    if not node.children:
        out.append(")")
        return
    inline_parts = _inline_parts(node, cache)
    if inline_parts is not None:
        for i, value in enumerate(inline_parts):
            if i:
                out.append(" ")
            out.append(value)
        out.append(")")
        return
    _write_node(node.children[0], indent + 2, out, cache)
    for child in node.children[1:]:
        out.append("\n")
        out.append(" " * (indent + 2))
        _write_node(child, indent + 2, out, cache)
    out.append(")")


def format_sexpr(root: Node) -> str:
    out: list[str] = []
    _write_node(root, 0, out, {})
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


def remove_descendants_by_head(root: Node, heads: set[str]) -> int:
    if root.atom is not None:
        return 0
    removed = 0
    kept: list[Node] = []
    for child in root.children:
        if child.atom is None and child.head() in heads:
            removed += 1
            continue
        if child.atom is None:
            removed += remove_descendants_by_head(child, heads)
        kept.append(child)
    root.children = kept
    return removed


def remove_descendants_by_rule(root: Node, rules: Iterable[FeatureRule], target: int) -> list[tuple[FeatureRule, int]]:
    active = [(rule, set(rule[1])) for rule in rules if target < rule[0]]
    if not active or root.atom is not None:
        return []

    counts = [0] * len(active)

    def visit(node: Node) -> None:
        kept: list[Node] = []
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


DescendantRemovalRule = tuple[set[str], str]
ContainingChildRemovalRule = tuple[str, str, str]


def apply_descendant_removal_rules(root: Node, warnings: list[str], rules: list[DescendantRemovalRule]) -> None:
    if not rules or root.atom is not None:
        return

    counts = [0] * len(rules)

    def visit(node: Node) -> None:
        kept: list[Node] = []
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


def apply_structural_removal_rules(
    root: Node,
    warnings: list[str],
    descendant_rules: list[DescendantRemovalRule],
    containing_child_rules: list[ContainingChildRemovalRule],
) -> None:
    if root.atom is not None:
        return
    if not descendant_rules and not containing_child_rules:
        return

    descendant_counts = [0] * len(descendant_rules)
    containing_counts = [0] * len(containing_child_rules)

    def visit(node: Node) -> None:
        kept: list[Node] = []
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


def remove_children_from_parents(root: Node, parents: set[str], children: set[str]) -> int:
    removed = 0
    for node in _walk(root):
        if node.head() in parents:
            before = len(node.children)
            node.children = [c for c in node.children if c.atom is not None or c.head() not in children]
            removed += before - len(node.children)
    return removed


ChildRemovalRule = tuple[set[str], set[str], str]
ChildValueRewriteRule = tuple[str, Optional[set[str]], set[str], str]


def apply_child_removal_rules(root: Node, warnings: list[str], rules: list[ChildRemovalRule]) -> None:
    if not rules:
        return

    counts = [0] * len(rules)
    parent_heads: set[str] = set()
    for parents, _children, _message in rules:
        parent_heads.update(parents)

    for node in _walk(root):
        node_head = node.head()
        if node_head not in parent_heads:
            continue

        kept: list[Node] = []
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


def apply_child_value_rewrite_rules(root: Node, warnings: list[str], rules: list[ChildValueRewriteRule]) -> None:
    if not rules:
        return

    counts = [0] * len(rules)
    all_heads: set[str] = set()
    for _mode, _parents, heads, _message in rules:
        all_heads.update(heads)

    for node in _walk(root):
        node_head = node.head()
        kept: list[Node] = []
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
                if mode == "bool-list":
                    if _bool_value(child.atom_at(1), True):
                        kept.append(atom(child_head))
                    counts[index] += 1
                    handled = True
                    break
                if mode == "presence-bool" and len(child.children) > 1:
                    value = child.atom_at(1).lower()
                    if value in {"yes", "true", "1"}:
                        child.children = child.children[:1]
                        kept.append(child)
                        counts[index] += 1
                        handled = True
                        break
                    if value in {"no", "false", "0"}:
                        counts[index] += 1
                        handled = True
                        break
            if not handled:
                kept.append(child)
        node.children = kept

    for index, count in enumerate(counts):
        if count:
            warnings.append(rules[index][3])


def remove_direct_children_by_head(root: Node, head: str) -> int:
    before = len(root.children)
    root.children = [c for c in root.children if c.atom is not None or c.head() != head]
    return before - len(root.children)


def rename_child_head_in_parents(root: Node, parents: set[str], old: str, new: str) -> int:
    changed = 0
    for node in _walk(root):
        if node.head() in parents:
            for child in node.children:
                if child.atom is None and child.head() == old and child.set_atom_at(0, new):
                    changed += 1
    return changed


def remove_atoms_from_headed_lists(root: Node, parents: set[str], atoms: set[str]) -> int:
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


def flatten_child_lists_to_atoms_in_parents(root: Node, parents: set[str], children: set[str]) -> int:
    changed = 0
    for node in _walk(root):
        if node.head() in parents:
            for i, child in enumerate(node.children):
                if child.atom is None and child.head() in children:
                    node.children[i] = atom(child.head())
                    changed += 1
    return changed


def downgrade_bool_lists_to_atoms(root: Node, heads: set[str]) -> int:
    changed = 0
    for node in _walk(root):
        kept: list[Node] = []
        for child in node.children:
            if child.atom is None and child.head() in heads:
                if _bool_value(child.atom_at(1), True):
                    kept.append(atom(child.head()))
                changed += 1
            else:
                kept.append(child)
        node.children = kept
    return changed


def downgrade_boolean_presence_nodes(root: Node, heads: set[str]) -> int:
    changed = 0
    for node in _walk(root):
        kept: list[Node] = []
        for child in node.children:
            if child.atom is None and child.head() in heads and len(child.children) > 1:
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
            if child.atom is None and child.head() in {"bold", "italic"} and len(child.children) > 1:
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
            if child.atom is not None or child.head() != "property":
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
            if child.atom is not None and child.atom == "hide":
                hidden = True
                changed += 1
            elif child.atom is None and child.head() == "hide":
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
    for node in _walk(root):
        if node.head() not in {"footprint", "module"}:
            continue
        kept: list[Node] = []
        for child in node.children:
            if child.atom is not None:
                kept.append(child)
                continue
            if child.head() == "property":
                name = child.atom_at(1)
                if name in {"Reference", "Value"}:
                    kind = "reference" if name == "Reference" else "value"
                    text = sexpr_list(atom("fp_text"), atom(kind), atom(child.atom_at(2), True))
                    for sub in child.children[3:]:
                        if sub.atom is None and sub.head() == "hide":
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
                if layer.atom is None and len(layer.children) >= 4:
                    if layer.atom_at(1).startswith("User.") and layer.atom_at(2) in {"front", "back", "auxiliary"}:
                        layer.set_atom_at(2, "user")
                        changed += 1
    return changed


def downgrade_pcbplotparams_bools(root: Node) -> int:
    changed = 0
    for node in _walk(root):
        if node.head() == "pcbplotparams":
            for child in node.children:
                if child.atom is None and len(child.children) > 1:
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
                if child.atom is None and child.head() == "fill":
                    insert_at = i
                    break
            node.children.insert(insert_at, sexpr_list(atom("filled_areas_thickness"), atom("no")))
            changed += 1
    return changed


def remove_nodes_containing_child(root: Node, parent_head: str, child_head: str) -> int:
    removed = 0
    for node in _walk(root):
        kept: list[Node] = []
        for child in node.children:
            if child.atom is None and child.head() == parent_head and child.child_list(child_head):
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
                if child.atom is not None and child.atom == old:
                    child.atom = new
                    changed += 1
    return changed


def downgrade_dimensions_to_text(root: Node) -> int:
    def convert(node: Node, inside_footprint: bool) -> int:
        inside = inside_footprint or node.head() in {"footprint", "module"}
        changed = 0
        kept: list[Node] = []
        for child in node.children:
            if child.atom is None and child.head() == "dimension":
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
                if child.atom is None:
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
        if child.atom is None and child.head() == "net":
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
            if child.atom is None:
                rewrite(child, head)

    rewrite(root)

    existing_codes = {
        _to_int(c.atom_at(1))
        for c in root.children
        if c.atom is None and c.head() == "net" and _is_int_atom(c.atom_at(1))
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
            if child.atom is None and child.head() == "net":
                last_net = i
            elif child.atom is None and child.head() in item_heads and first_item == len(root.children):
                first_item = i

        # Legacy net declarations must stay after setup metadata and before board items.
        insert_at = last_net + 1 if last_net >= 0 else first_item

        for offset, (name, code) in enumerate(new_entries):
            root.children.insert(insert_at + offset, sexpr_list(atom("net"), atom(str(code)), atom(name, True)))
        changed += len(new_entries)

    return changed


def remove_introduced(root: Node, target: int, rules: Iterable[FeatureRule]) -> list[str]:
    warnings: list[str] = []
    for (min_version, _heads, reason), removed in remove_descendants_by_rule(root, rules, target):
        if removed:
            warnings.append(f"removed {removed} node(s) introduced in {min_version}: {reason}")
    return warnings


def _warn_if_changed(warnings: list[str], count: int, message: str) -> None:
    if count > 0:
        warnings.append(message)


def _apply_when(warnings: list[str], condition: bool, rewrite: Callable[[], int], message: str) -> None:
    if condition:
        _warn_if_changed(warnings, rewrite(), message)


def _queue_child_removal(
    rules: list[ChildRemovalRule],
    condition: bool,
    parents: set[str],
    children: set[str],
    message: str,
) -> None:
    if condition:
        rules.append((parents, children, message))


def _queue_descendant_removal(
    rules: list[DescendantRemovalRule],
    condition: bool,
    heads: set[str],
    message: str,
) -> None:
    if condition:
        rules.append((heads, message))


def apply_downgrade_rules(doc: Document, target: int) -> list[str]:
    root = doc.root
    warnings: list[str] = []

    if doc.kind == "symbol-library":
        child_removals: list[ChildRemovalRule] = []
        warnings.extend(remove_introduced(root, target, SYMBOL_RULES))
        _apply_when(warnings, target < 20231120, lambda: remove_direct_children_by_head(root, "generator_version"), "removed symbol library generator_version fields")
        _apply_when(warnings, target < 20241209, lambda: remove_descendants_by_head(root, {"embedded_fonts"}), "removed symbol library embedded_fonts fields")
        _apply_when(warnings, target < 20240108, lambda: downgrade_font_style_lists_to_atoms(root), "downgraded symbol library font bold/italic bool fields")
        _queue_child_removal(child_removals, target <= 20241209, {"font"}, {"face"}, "removed symbol library font face fields")
        if target < 20241004:
            _warn_if_changed(warnings, downgrade_bool_lists_to_atoms(root, {"hide"}), "downgraded symbol library boolean hide fields")
            _warn_if_changed(warnings, flatten_child_lists_to_atoms_in_parents(root, {"pin_names", "pin_numbers"}, {"hide"}), "downgraded symbol pin visibility fields")
        if target < 20241209:
            _warn_if_changed(warnings, ensure_legacy_property_ids(root), "added legacy symbol property ids")
            _warn_if_changed(warnings, move_property_hide_to_effects(root), "moved symbol property hide flags to effects")
        _queue_child_removal(child_removals, target < 20251024, {"symbol"}, {"in_pos_files"}, "removed symbol library position file flags")
        _queue_child_removal(child_removals, target < 20250324, {"symbol"}, {"duplicate_pin_numbers_are_jumpers"}, "removed symbol library jumper pin-number flags")
        _queue_child_removal(child_removals, target < 20250227, {"symbol"}, {"power"}, "removed symbol library power class flags")
        _queue_child_removal(child_removals, target < 20251024, {"property"}, {"show_name", "do_not_autoplace"}, "removed symbol property formatting fields")
        apply_child_removal_rules(root, warnings, child_removals)

    elif doc.kind == "schematic":
        child_removals = []
        descendant_removals: list[DescendantRemovalRule] = []
        warnings.extend(remove_introduced(root, target, SCHEMATIC_RULES))
        _apply_when(warnings, target < 20231120, lambda: remove_direct_children_by_head(root, "generator_version"), "removed schematic generator_version fields")
        _queue_descendant_removal(descendant_removals, target < 20260326, {"locked"}, "removed schematic locked fields introduced after target version")
        _queue_descendant_removal(descendant_removals, target < 20260306, {"embedded_fonts"}, "removed schematic embedded_fonts fields")
        _queue_descendant_removal(descendant_removals, target < 20250827, {"body_styles", "body_style"}, "removed schematic custom body style fields")
        apply_descendant_removal_rules(root, warnings, descendant_removals)
        _queue_child_removal(child_removals, target < 20250114, {"text", "text_box", "textbox"}, {"exclude_from_sim"}, "removed schematic text simulation flags")
        _queue_child_removal(child_removals, target < 20260306, {"sheet"}, {"exclude_from_sim", "in_bom", "on_board", "dnp"}, "removed schematic sheet assembly/simulation flags")
        _apply_when(warnings, target <= 20230121, lambda: remove_descendants_by_head(root, {"exclude_from_sim"}), "removed schematic simulation exclusion flags")
        _queue_child_removal(child_removals, target < 20251024, {"symbol"}, {"in_pos_files"}, "removed schematic symbol position file flags")
        _queue_child_removal(child_removals, target < 20250324, {"symbol"}, {"duplicate_pin_numbers_are_jumpers"}, "removed schematic library symbol jumper pin-number flags")
        _queue_child_removal(child_removals, target < 20250227, {"symbol"}, {"power"}, "removed schematic library symbol power class flags")
        if target < 20241004:
            _warn_if_changed(warnings, downgrade_bool_lists_to_atoms(root, {"hide"}), "downgraded schematic boolean hide fields")
            _warn_if_changed(warnings, flatten_child_lists_to_atoms_in_parents(root, {"pin_names", "pin_numbers"}, {"hide"}), "downgraded schematic symbol pin visibility fields")
        _apply_when(warnings, target < 20240108, lambda: downgrade_font_style_lists_to_atoms(root), "downgraded schematic font bold/italic bool fields")
        _queue_child_removal(child_removals, target <= 20250114, {"font"}, {"face"}, "removed schematic font face fields")
        if target < 20241209:
            _warn_if_changed(warnings, ensure_legacy_property_ids(root), "added legacy schematic property ids")
            _warn_if_changed(warnings, move_property_hide_to_effects(root), "moved schematic property hide flags to effects")
        _queue_child_removal(child_removals, target < 20231120, {"symbol", "sheet"}, {"fields_autoplaced"}, "removed schematic symbol/sheet fields_autoplaced fields")
        _queue_child_removal(child_removals, target < 20251028, {"property"}, {"show_name", "do_not_autoplace"}, "removed schematic property formatting fields")
        _apply_when(warnings, target < 20260306, lambda: remove_direct_children_by_head(root, "group"), "removed schematic group nodes")
        apply_child_removal_rules(root, warnings, child_removals)

    elif doc.kind in {"board", "footprint"}:
        child_removals = []
        child_value_rewrites: list[ChildValueRewriteRule] = []
        descendant_removals: list[DescendantRemovalRule] = []
        containing_child_removals: list[ContainingChildRemovalRule] = []
        warnings.extend(remove_introduced(root, target, BOARD_RULES))
        if target < 20260410:
            containing_child_removals.append(("model", "type", "removed typed/extruded 3D model blocks"))
        _queue_descendant_removal(descendant_removals, target < 20250228, {"covering", "plugging", "filling", "capping"}, "removed IPC-4761 via protection fields")
        _queue_descendant_removal(descendant_removals, target < 20231212, {"unlocked"}, "removed PCB text keep-upright unlock fields")
        apply_structural_removal_rules(root, warnings, descendant_removals, containing_child_removals)
        _apply_when(warnings, target < 20260513, lambda: replace_atom_values_in_parents(root, {"mode"}, "thieving", "polygon"), "downgraded copper thieving fill modes to polygon fill")
        _queue_child_removal(child_removals, target >= 20220225, {"footprint", "module"}, {"tedit"}, "removed obsolete footprint tedit fields")
        _queue_child_removal(child_removals, target >= 20200628, {"setup"}, {"visible_elements"}, "removed obsolete board visible_elements settings")
        _apply_when(warnings, target < 20240703, lambda: downgrade_user_layer_types(root), "removed user-layer type qualifiers")
        if target < 20241010:
            _queue_child_removal(child_removals, True, {"gr_line", "gr_arc", "gr_circle", "gr_rect", "gr_poly", "fp_line", "fp_arc", "fp_circle", "fp_rect", "fp_poly"}, {"solder_mask_margin"}, "removed graphic solder_mask_margin fields")
        if target < 20241030:
            _queue_child_removal(child_removals, True, {"style"}, {"arrow_direction"}, "removed dimension arrow direction fields")
        _queue_child_removal(child_removals, target < 20241009, {"zone"}, {"placement"}, "removed zone placement fields")
        _queue_child_removal(child_removals, target < 20241007, {"segment", "arc"}, {"solder_mask_margin", "solder_mask_layer"}, "removed track soldermask layer/margin fields")
        _queue_child_removal(child_removals, target < 20240617, {"table_cell"}, {"angle"}, "removed PCB table cell angle fields")
        if target < 20250228:
            _warn_if_changed(warnings, downgrade_tenting_to_legacy_atoms(root), "downgraded tenting front/back bool lists to legacy atom syntax")
        if target < 20231212:
            _warn_if_changed(warnings, downgrade_boolean_presence_nodes(root, {"locked", "hide"}), "downgraded board/footprint boolean locked/hide fields")
            _queue_child_removal(child_removals, True, {"model"}, {"hide"}, "removed legacy-incompatible 3D model hide fields")
        _apply_when(warnings, target < 20231014, lambda: remove_direct_children_by_head(root, "generator_version"), "removed board/footprint generator_version fields")
        if target < 20230924:
            _warn_if_changed(warnings, downgrade_pcbplotparams_bools(root), "downgraded pcbplotparams boolean values")
            _warn_if_changed(warnings, downgrade_shape_fill_no_to_none(root), "downgraded PCB shape fill no values to none")
        if target < 20230730:
            _queue_child_removal(child_removals, True, {"gr_line", "gr_arc", "gr_circle", "gr_rect", "gr_poly", "gr_curve", "fp_line", "fp_arc", "fp_circle", "fp_rect", "fp_poly", "fp_curve"}, {"net"}, "removed PCB graphic shape net connectivity fields")
        if target < 20240108:
            _queue_child_removal(child_removals, True, {"group"}, {"locked"}, "removed group locked fields")
            child_value_rewrites.append(("bool-list", {"font"}, {"bold", "italic"}, "downgraded PCB font bold/italic bool fields"))
        _apply_when(warnings, target < 20230620, lambda: downgrade_pcb_footprint_fields(root), "downgraded PCB footprint fields to legacy storage")
        if target < 20231231:
            parents = {"footprint", "module", "pad", "via", "segment", "arc", "zone", "gr_line", "gr_arc", "gr_circle", "gr_rect", "gr_poly", "gr_curve", "gr_text", "fp_line", "fp_arc", "fp_circle", "fp_rect", "fp_poly", "fp_curve", "fp_text"}
            _warn_if_changed(warnings, rename_child_head_in_parents(root, parents, "uuid", "tstamp"), "renamed footprint uuid fields back to legacy tstamp")
            _warn_if_changed(warnings, rename_child_head_in_parents(root, {"group", "generated"}, "uuid", "id"), "renamed board group/generated uuid fields back to id")
        _queue_child_removal(child_removals, target < 20250324, {"footprint"}, {"duplicate_pad_numbers_are_jumpers", "jumper_pad_groups"}, "removed footprint jumper pad fields")
        _apply_when(warnings, target <= 20221018, lambda: remove_atoms_from_headed_lists(root, {"attr"}, {"dnp"}), "removed footprint dnp attributes")
        _queue_child_removal(child_removals, target < 20250309, {"placement"}, {"component_class"}, "removed rule_area component_class placement sources")
        _apply_when(warnings, target < 20250222, lambda: downgrade_shape_hatch_fills(root), "downgraded PCB shape hatch fills")
        _queue_child_removal(child_removals, target < 20250210, {"gr_text_box", "fp_text_box"}, {"knockout"}, "removed PCB text box knockout fields")
        _apply_when(warnings, target < 20250210, lambda: ensure_zone_filled_areas_thickness(root), "tagged cached zone fills as polygon fills")
        _queue_child_removal(child_removals, target <= 20241229, {"font"}, {"face"}, "removed PCB font face fields")
        if target <= 20221018:
            child_value_rewrites.append(("presence-bool", None, {"free"}, "downgraded free via fields"))
        if target <= 20221018:
            _queue_child_removal(child_removals, True, {"pad", "via"}, {"remove_unused_layers"}, "removed pad/via remove_unused_layers fields")
        if target < 20241030:
            child_value_rewrites.insert(0, ("bool-list", None, {"suppress_zeroes", "keep_text_aligned"}, "downgraded dimension boolean fields to legacy atom syntax"))
        apply_child_value_rewrite_rules(root, warnings, child_value_rewrites)
        if target <= 20221018:
            _warn_if_changed(warnings, downgrade_dimensions_to_text(root), "downgraded PCB dimensions to legacy text annotations")
            _warn_if_changed(warnings, remove_descendants_by_head(root, {"locked"}), "removed legacy-incompatible locked fields")
        _queue_child_removal(child_removals, target < 20251101, {"pad", "via"}, {"front_post_machining", "back_post_machining"}, "removed pad/via post-machining fields")
        apply_child_removal_rules(root, warnings, child_removals)
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
