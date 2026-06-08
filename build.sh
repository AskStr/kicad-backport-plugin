#!/usr/bin/env sh
set -eu

usage() {
    echo "Usage: $0 [--version VERSION]" >&2
}

version=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        --version|-v)
            if [ "$#" -lt 2 ]; then
                usage
                exit 2
            fi
            version="$2"
            shift 2
            ;;
        --version=*)
            version=${1#--version=}
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            if [ -n "$version" ]; then
                usage
                exit 2
            fi
            version="$1"
            shift
            ;;
    esac
done

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
plugin_root=$script_dir
dist_root=$plugin_root/dist
package_root=$dist_root/kicad-backport
archive_path=$dist_root/kicad-backport.zip

if command -v python3 >/dev/null 2>&1; then
    python_cmd=python3
elif command -v python >/dev/null 2>&1; then
    python_cmd=python
else
    echo "Python was not found; cannot read plugin.json or create the archive." >&2
    exit 1
fi

if [ -z "$version" ]; then
    version=$("$python_cmd" - "$plugin_root/plugin.json" <<'PY'
import json
import sys
from pathlib import Path

print(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["version"])
PY
)
fi

rm -rf "$dist_root"
mkdir -p "$package_root"

for item in __init__.py plugin.json README.md requirements.txt; do
    cp "$plugin_root/$item" "$package_root/"
done

for dir in assets legacy plugin docs; do
    cp -R "$plugin_root/$dir" "$package_root/"
done

find "$package_root" -type d -name __pycache__ -prune -exec rm -rf {} +
find "$package_root" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

for file in \
    __init__.py \
    plugin.json \
    README.md \
    requirements.txt \
    plugin/plugin.py \
    plugin/backport_core.py \
    plugin/i18n.py
do
    if [ ! -f "$package_root/$file" ]; then
        echo "Package is missing required file: kicad-backport/$file" >&2
        exit 1
    fi
done

"$python_cmd" - "$dist_root" "$archive_path" <<'PY'
import sys
import zipfile
from pathlib import Path

dist_root = Path(sys.argv[1])
archive_path = Path(sys.argv[2])
package_root = dist_root / "kicad-backport"
required = [
    "__init__.py",
    "plugin.json",
    "README.md",
    "requirements.txt",
    "plugin/plugin.py",
    "plugin/backport_core.py",
    "plugin/i18n.py",
]

with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(package_root.rglob("*")):
        if path.is_file():
            archive.write(path, path.relative_to(dist_root).as_posix())

with zipfile.ZipFile(archive_path, "r") as archive:
    entries = set(archive.namelist())
    if not any(name.startswith("kicad-backport/") for name in entries):
        raise SystemExit("Archive does not contain the kicad-backport directory.")
    for file in required:
        entry = "kicad-backport/" + file
        if entry not in entries:
            raise SystemExit("Archive is missing required file: " + entry)
PY

echo "Built unpacked package: $package_root"
echo "Built archive: $archive_path"
echo "Version: $version"
