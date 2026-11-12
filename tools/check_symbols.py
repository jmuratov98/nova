#!/usr/bin/env python3
"""Checks each subsystem's object against the declaration (ADR 0003, layer 3).

Run after every subsystem has been partially linked and made to hide what it doesn't export, so
that a subsystem's global symbols are exactly its exports. Every undefined symbol in a subsystem's
object must be an export of a subsystem that it declares as a dependency.

    check_symbols.py [--arch ARCH] --build-dir DIR --nm NM
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import subsystems
from subsystems import Declaration


@dataclass
class Symbols:
    exported: set[str] = field(default_factory=set)
    private: set[str] = field(default_factory=set)
    undefined: set[str] = field(default_factory=set)


def read_symbols(nm: list[str], path: Path) -> Symbols:
    found = Symbols()
    output = subprocess.run([*nm, str(path)], capture_output=True, text=True, check=True).stdout
    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        kind, name = parts[-2], parts[-1]
        if kind in ("U", "w", "v"):
            found.undefined.add(name)
        elif kind.isupper() or kind == "u":
            found.exported.add(name)
        else:
            found.private.add(name)
    return found


def source_of(
    declaration: Declaration, build_dir: Path, nm: list[str], name: str, symbol: str, role: str
) -> str:
    """The source file that a symbol of a subsystem is in, which the partial link has merged
    away, or the subsystem's name if no single file can be found. The role says whether the file
    defines the symbol ("exported") or references it ("undefined")."""
    for source in declaration.sources(name):
        compiled = build_dir / "obj" / name / f"{Path(source).name}.o"
        if symbol in getattr(read_symbols(nm, compiled), role):
            return source
    return name


def check(declaration: Declaration, build_dir: Path, nm: list[str]) -> list[str]:
    objects = {
        name: read_symbols(nm, build_dir / "sub" / f"{name}.o") for name in declaration.subsystems
    }
    unprefixed = {
        symbol
        for subsystem in declaration.subsystems.values()
        for symbol in subsystem.unprefixed_exports
    }

    errors = []
    for name, subsystem in declaration.subsystems.items():
        for symbol in sorted(objects[name].exported):
            exempt = (
                symbol in subsystem.unprefixed_exports
                or declaration.entry_points.get(symbol) == name
            )
            if not symbol.startswith(subsystem.prefix) and not exempt:
                where = source_of(declaration, build_dir, nm, name, symbol, "exported")
                errors.append(
                    f"{where}: error: export-prefix: {name} exports '{symbol}', which must "
                    f"start with '{subsystem.prefix}'"
                )

        allowed = set(unprefixed)
        for dependency in subsystem.dependencies:
            allowed |= objects[dependency].exported
        if name == subsystems.PORT:
            allowed |= set(declaration.entry_points)

        for symbol in sorted(objects[name].undefined - allowed):
            exporters = [o for o, found in objects.items() if symbol in found.exported]
            owners = [o for o, found in objects.items() if o != name and symbol in found.private]
            where = source_of(declaration, build_dir, nm, name, symbol, "undefined")
            if exporters:
                errors.append(
                    f"{where}: error: undeclared-dependency: {name} references '{symbol}', which "
                    f"{exporters[0]} exports, but {name} doesn't declare {exporters[0]} as a "
                    f"dependency"
                )
            elif owners:
                errors.append(
                    f"{where}: error: private-symbol: {name} references '{symbol}', which is "
                    f"private to {owners[0]}"
                )
            else:
                errors.append(
                    f"{where}: error: unresolved-symbol: {name} references '{symbol}', which no "
                    f"subsystem defines"
                )
    return errors


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--arch", default="x86_64")
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--nm", default="llvm-nm")
    args = parser.parse_args(argv)

    try:
        declaration = subsystems.load(args.root, args.arch)
    except subsystems.DeclarationError as error:
        print(error, file=sys.stderr)
        return 1

    errors = check(declaration, args.build_dir, shlex.split(args.nm))
    for message in errors:
        print(message, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
