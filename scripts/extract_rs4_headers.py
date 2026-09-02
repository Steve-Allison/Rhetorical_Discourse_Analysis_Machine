"""CLI tool to extract declared relation and signal inventories from RS4 files."""

import json
from pathlib import Path
import sys

from rdam.rst.erst.rs4 import RS4Reader


def extract_headers_from_path(path: Path) -> dict[str, dict[str, list[str]]]:
    """Scan a path (file or directory) and extract unique relations and signal types."""
    files = [path] if path.is_file() else sorted(path.glob("**/*.rs4"))

    relations: dict[str, set[str]] = {}
    sigtypes: dict[str, set[str]] = {}

    for file_path in files:
        doc = RS4Reader.read_file(file_path)
        for rel_name, rel_type in doc.relations.items():
            relations.setdefault(rel_type, set()).add(rel_name)
        for sig_type, subtypes in doc.sigtypes.items():
            sigtypes.setdefault(sig_type, set()).update(subtypes)

    return {
        "relations": {k: sorted(v) for k, v in sorted(relations.items())},
        "signal_types": {k: sorted(v) for k, v in sorted(sigtypes.items())},
    }


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/extract_rs4_headers.py <path-to-rs4-file-or-dir>")
        sys.exit(1)

    target_path = Path(sys.argv[1])
    if not target_path.exists():
        print(f"Path does not exist: {target_path}")
        sys.exit(1)

    result = extract_headers_from_path(target_path)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
