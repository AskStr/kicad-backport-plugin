#!/usr/bin/env sh
set -eu

usage() {
    echo "Usage: $0 [--version VERSION] [--format zip|tar.gz|all]" >&2
}

version=""
format="zip"
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
        --format|-f)
            if [ "$#" -lt 2 ]; then
                usage
                exit 2
            fi
            format="$2"
            shift 2
            ;;
        --format=*)
            format=${1#--format=}
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

case "$format" in
    zip|tar.gz|all)
        ;;
    *)
        usage
        exit 2
        ;;
esac

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
plugin_root=$script_dir
dist_root=$plugin_root/dist
package_root=$dist_root/kicad-backport
zip_archive_path=$dist_root/kicad-backport.zip
tar_gz_archive_path=$dist_root/kicad-backport.tar.gz

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

"$python_cmd" - "$dist_root" "$zip_archive_path" "$tar_gz_archive_path" "$format" <<'PY'
import sys
import tarfile
import zipfile
from pathlib import Path

dist_root = Path(sys.argv[1])
zip_archive_path = Path(sys.argv[2])
tar_gz_archive_path = Path(sys.argv[3])
archive_format = sys.argv[4]
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

def assert_entries(entries, archive_name):
    entries = set(entries)
    bad_entries = [name for name in entries if "\\" in name]
    if bad_entries:
        raise SystemExit(
            archive_name + " contains a Windows path separator: " + bad_entries[0]
        )
    if not any(name.startswith("kicad-backport/") for name in entries):
        raise SystemExit(archive_name + " does not contain the kicad-backport directory.")
    for file in required:
        entry = "kicad-backport/" + file
        if entry not in entries:
            raise SystemExit(archive_name + " is missing required file: " + entry)

def build_zip(archive_path):
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(package_root.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(dist_root).as_posix())

    with zipfile.ZipFile(archive_path, "r") as archive:
        assert_entries(archive.namelist(), "Archive")

def build_tar_gz(archive_path):
    with tarfile.open(archive_path, "w:gz") as archive:
        for path in sorted(package_root.rglob("*")):
            arcname = path.relative_to(dist_root).as_posix()
            archive.add(path, arcname=arcname, recursive=False)

    with tarfile.open(archive_path, "r:gz") as archive:
        assert_entries(archive.getnames(), "Archive")

if archive_format in ("zip", "all"):
    build_zip(zip_archive_path)
if archive_format in ("tar.gz", "all"):
    build_tar_gz(tar_gz_archive_path)
PY

echo "Built unpacked package: $package_root"
if [ "$format" = zip ] || [ "$format" = all ]; then
    echo "Built archive: $zip_archive_path"
fi
if [ "$format" = tar.gz ] || [ "$format" = all ]; then
    echo "Built archive: $tar_gz_archive_path"
fi
echo "Version: $version"
