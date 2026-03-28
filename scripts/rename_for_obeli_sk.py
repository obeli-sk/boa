#!/usr/bin/env python3
"""
Renames boa crate package names to the `obeli-sk-` prefix and sets the workspace
version, so they can be published to crates.io without conflicting with upstream.

Usage: python3 scripts/rename_for_obeli_sk.py <version>
Example: python3 scripts/rename_for_obeli_sk.py 1.0.0-obeli-sk.1
"""

import re
import sys
from pathlib import Path

if len(sys.argv) != 2:
    print(f"Usage: {sys.argv[0]} <version>", file=sys.stderr)
    sys.exit(1)

version = sys.argv[1]

# Map: original package name -> published crate name (hyphens for crates.io)
RENAMES = {
    "boa_ast": "obeli-sk-boa-ast",
    "boa_engine": "obeli-sk-boa-engine",
    "boa_gc": "obeli-sk-boa-gc",
    "boa_icu_provider": "obeli-sk-boa-icu-provider",
    "boa_interner": "obeli-sk-boa-interner",
    "boa_macros": "obeli-sk-boa-macros",
    "boa_parser": "obeli-sk-boa-parser",
    "boa_runtime": "obeli-sk-boa-runtime",
    "boa_string": "obeli-sk-boa-string",
    "boa_wintertc": "obeli-sk-boa-wintertc",
    "small_btree": "obeli-sk-small-btree",
    "tag_ptr": "obeli-sk-tag-ptr",
}

# Map: original package name -> path relative to repo root
CRATE_PATHS = {
    "boa_ast": "core/ast",
    "boa_engine": "core/engine",
    "boa_gc": "core/gc",
    "boa_icu_provider": "core/icu_provider",
    "boa_interner": "core/interner",
    "boa_macros": "core/macros",
    "boa_parser": "core/parser",
    "boa_runtime": "core/runtime",
    "boa_string": "core/string",
    "boa_wintertc": "core/wintertc",
    "small_btree": "utils/small_btree",
    "tag_ptr": "utils/tag_ptr",
}

root = Path(__file__).parent.parent

# ── 1. Update workspace Cargo.toml ──────────────────────────────────────────

root_cargo = root / "Cargo.toml"
content = root_cargo.read_text()

# Update [workspace.package] version
content = re.sub(
    r'^(version\s*=\s*)"[^"]+"',
    rf'\1"{version}"',
    content,
    flags=re.MULTILINE,
)

# For each renamed crate, update its entry in [workspace.dependencies]:
#   Before: boa_ast = { version = "~1.0.0-dev", path = "core/ast" }
#   After:  boa_ast = { package = "obeli-sk-boa-ast", version = "1.0.0-obeli-sk.1", path = "core/ast" }
#
# The workspace-dep key stays as the original name so that `boa_ast.workspace = true`
# in individual crates continues to work; `package` tells cargo the real crate name.

for old_name, new_name in RENAMES.items():
    # Match an inline-table workspace dependency line for this crate.
    pattern = rf'^({re.escape(old_name)}\s*=\s*\{{)([^\n\}}]+)(\}})'

    def make_replacer(new_name=new_name):
        def replacer(m):
            prefix, body, suffix = m.group(1), m.group(2), m.group(3)
            # Insert `package` if not already present
            if "package" not in body:
                body = f' package = "{new_name}",' + body
            # Replace the version constraint
            body = re.sub(r'version\s*=\s*"[^"]*"', f'version = "{version}"', body)
            return prefix + body + suffix
        return replacer

    content = re.sub(pattern, make_replacer(), content, flags=re.MULTILINE)

root_cargo.write_text(content)
print(f"Updated {root_cargo}")

# ── 2. Rename [package] name in each individual crate ────────────────────────

for old_name, new_name in RENAMES.items():
    cargo_toml = root / CRATE_PATHS[old_name] / "Cargo.toml"
    if not cargo_toml.exists():
        print(f"WARNING: {cargo_toml} not found, skipping")
        continue

    content = cargo_toml.read_text()
    # If the crate has a hardcoded version (not version.workspace = true), update it.
    content = re.sub(
        r'^(version\s*=\s*)"[^"]+"',
        rf'\1"{version}"',
        content,
        count=1,
        flags=re.MULTILINE,
    )
    # count=1: only replace the first occurrence, which is [package] name.
    # Other sections (e.g. [lib]) may also have a `name` field that must
    # keep the original underscore form (lib target names cannot have hyphens).
    updated = re.sub(
        rf'^(name\s*=\s*)"({re.escape(old_name)})"',
        rf'\1"{new_name}"',
        content,
        count=1,
        flags=re.MULTILINE,
    )
    if updated == content:
        print(f"WARNING: no name replacement made in {cargo_toml}")
    else:
        cargo_toml.write_text(updated)
        print(f"  {old_name!s:30s} -> {new_name}")

print(f"\nDone. Version set to {version!r}.")
