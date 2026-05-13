#!/usr/bin/env python3
"""Scaffold Enterprise Agent Memory Pack into a target directory."""

import shutil
import sys
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        print("Usage: scaffold_pack.py <target_dir> [--overwrite]")
        sys.exit(1)

    target = Path(sys.argv[1])
    overwrite = "--overwrite" in sys.argv

    pack_source = Path(__file__).parent.parent / "assets" / "enterprise-agent-memory-pack"

    if not pack_source.exists():
        print(f"Pack source not found: {pack_source}")
        sys.exit(1)

    if target.exists() and not overwrite:
        print(f"Target already exists: {target}. Use --overwrite to replace.")
        sys.exit(1)

    if target.exists() and overwrite:
        shutil.rmtree(target)

    shutil.copytree(pack_source, target)
    print(f"Enterprise Agent Memory Pack scaffolded to: {target}")


if __name__ == "__main__":
    main()
