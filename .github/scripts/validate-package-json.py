#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def get_actual_files():
    """Get all Python files from walter_modem folder (excluding .pyi type stubs)."""
    files = []
    walter_modem_dir = Path("walter_modem")

    for py_file in sorted(walter_modem_dir.glob("*.py")):
        if py_file.is_file():
            files.append(py_file.relative_to(Path(".")))

    for py_file in sorted((walter_modem_dir / "mixins").glob("*.py")):
        if py_file.is_file():
            files.append(py_file.relative_to(Path(".")))

    return [str(f) for f in files]


def get_github_urls(files):
    """Generate GitHub URLs for package.json format."""
    return [[f, f"github:QuickSpot/walter-micropython/{f}"] for f in files]


def validate_and_update_package_json():
    """
    Validates and syncs package.json with actual files in walter_modem folder.
    Returns: (changed: bool, added: list, removed: list)
    """
    package_json_path = "package.json"

    with open(package_json_path, "r") as f:
        package_data = json.load(f)

    actual_files = get_actual_files()
    correct_urls = get_github_urls(actual_files)

    current_urls = package_data.get("urls", [])
    current_files = [url[0] for url in current_urls]

    actual_set = set(actual_files)
    current_set = set(current_files)
    added = sorted(actual_set - current_set)
    removed = sorted(current_set - actual_set)

    if added or removed:
        package_data["urls"] = correct_urls

        with open(package_json_path, "w") as f:
            f.write("{\n")
            f.write('    "urls": [\n')
            for i, url_pair in enumerate(correct_urls):
                f.write(f'        {json.dumps(url_pair)}')
                f.write("," if i < len(correct_urls) - 1 else "")
                f.write("\n")
            f.write("    ],\n")
            f.write(f'    "version": "{package_data["version"]}"\n')
            f.write("}\n")

        return True, added, removed

    return False, [], []


if __name__ == "__main__":
    try:
        changed, added, removed = validate_and_update_package_json()

        if changed:
            if added:
                print(f"Added files: {added}")
            if removed:
                print(f"Removed files: {removed}")
            print(f"Updated package.json")
            sys.exit(1)  # Exit 1 to signal changes for GitHub Actions
        else:
            print("package.json is in sync")
            sys.exit(0)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)
