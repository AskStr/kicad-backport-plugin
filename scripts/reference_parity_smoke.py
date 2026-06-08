import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REFERENCE = ROOT.parent / "kicad-backport-cplus"


def warning_messages(text):
    messages = set()
    pattern = r"""['"]((?:removed|downgraded|renamed|normalized|added|approximated|split|moved)[^'"]+)['"]"""
    for match in re.finditer(pattern, text):
        messages.add(match.group(1))
    return messages


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    reference = Path(argv[0]) if argv else DEFAULT_REFERENCE
    rules_path = reference / "src" / "kicad_backport_rules.cpp"
    python_path = ROOT / "plugin" / "backport_core.py"
    if not rules_path.exists():
        raise RuntimeError("C++ reference rules were not found: {0}".format(rules_path))

    cpp_messages = warning_messages(rules_path.read_text(encoding="utf-8"))
    python_messages = warning_messages(python_path.read_text(encoding="utf-8"))
    missing = sorted(cpp_messages - python_messages)
    if missing:
        print("Python rule warning coverage is missing {0} C++ message(s):".format(len(missing)))
        for message in missing:
            print("- " + message)
        return 1
    print(
        "reference parity smoke ok: {0} C++ rule warning message(s) covered".format(
            len(cpp_messages)
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
