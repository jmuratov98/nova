#!/usr/bin/env python3
"""Nova's central subsystem declaration.

kernel/subsystems.toml is the one place that says which subsystems exist and what each may use
(ADR 0002, ADR 0003). This reads it, checks it against the directories on disk, and
generates what the build needs from it, which is each subsystem's include paths and sources.

    subsystems.py check    [--arch ARCH]
    subsystems.py makefile [--arch ARCH] --output FILE

Run from the repository root, or pass --root.
"""

from __future__ import annotations

import argparse
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DECLARATION = "kernel/subsystems.toml"
KERNEL_DIR = "kernel"
THIRD_PARTY_DIR = "third_party"
SOURCE_SUFFIXES = (".c", ".S")
KEYS = {"dependencies", "third_party_headers", "unprefixed_exports"}

# The port is the one subsystem whose directory isn't kernel/<name>/. kernel/port/include/ holds
# the port interface, and kernel/port/<arch>/ the port for one architecture.
PORT = "port"
PORT_INTERFACE_DIR = f"{KERNEL_DIR}/{PORT}/include"
PORT_FRAGMENT = "port.mk"


class DeclarationError(Exception):
    """A rule that the declaration breaks. str() is the message the build prints."""

    def __init__(self, rule: str, message: str) -> None:
        super().__init__(f"{DECLARATION}: error: {rule}: {message}")


@dataclass(frozen=True)
class Subsystem:
    name: str
    dependencies: tuple[str, ...]
    unprefixed_exports: tuple[str, ...]
    directory: str  # where its sources and private headers are
    public_includes: tuple[str, ...]  # what a subsystem that depends on it compiles with
    third_party_headers: tuple[str, ...]  # the vendored headers it may include, as files

    @property
    def prefix(self) -> str:
        return f"{self.name}_"

    @property
    def third_party_includes(self) -> tuple[str, ...]:
        """The directories that hold its vendored headers, which the compiler has to search."""
        return tuple(
            dict.fromkeys(Path(header).parent.as_posix() for header in self.third_party_headers)
        )


@dataclass(frozen=True)
class Declaration:
    root: Path
    subsystems: dict[str, Subsystem]  # dependencies come before their dependents
    entry_points: dict[str, str]  # entry point -> the subsystem that implements it

    def includes(self, name: str) -> list[str]:
        """The directories a subsystem compiles with, in search order, and nothing else."""
        subsystem = self.subsystems[name]
        found = [subsystem.directory, *subsystem.public_includes]
        for dependency in subsystem.dependencies:
            found.extend(self.subsystems[dependency].public_includes)
        found.extend(subsystem.third_party_includes)
        return list(dict.fromkeys(found))

    def may_include(self, name: str) -> tuple[list[str], list[str]]:
        """Where a header that a subsystem includes may be: the directories that are its own or
        its dependencies' public ones, and the vendored headers that it is permitted, as files. The
        compiler searches a vendored header's whole directory, so only this tells them apart."""
        subsystem = self.subsystems[name]
        directories = [subsystem.directory, *subsystem.public_includes]
        for dependency in subsystem.dependencies:
            directories.extend(self.subsystems[dependency].public_includes)
        return list(dict.fromkeys(directories)), list(subsystem.third_party_headers)

    def sources(self, name: str) -> list[str]:
        """The files a subsystem compiles. Its directory is flat."""
        directory = self.root / self.subsystems[name].directory
        files = sorted(p for p in directory.iterdir() if p.suffix in SOURCE_SUFFIXES)
        return [p.relative_to(self.root).as_posix() for p in files]

    def files(self) -> list[str]:
        """Every file under kernel/ that a check reads, so that a change to one reruns it."""
        found = (self.root / KERNEL_DIR).rglob("*")
        return sorted(p.relative_to(self.root).as_posix() for p in found if p.is_file())


def load(root: Path, arch: str) -> Declaration:
    """Reads the declaration, and raises DeclarationError if it breaks a rule."""
    path = root / DECLARATION
    try:
        data = tomllib.loads(path.read_text())
    except FileNotFoundError:
        raise DeclarationError("missing-declaration", "the file doesn't exist") from None
    except tomllib.TOMLDecodeError as error:
        raise DeclarationError("malformed-declaration", str(error)) from None

    entry_points = data.get("entry_points", {})
    declared = data.get("subsystem", {})
    for name, table in declared.items():
        unknown = sorted(set(table) - KEYS)
        if unknown:
            raise DeclarationError(
                "malformed-declaration", f"{name} has unknown keys: {', '.join(unknown)}"
            )

    _check_disk(root, arch, sorted(declared))
    dependencies = {name: tuple(table.get("dependencies", ())) for name, table in declared.items()}
    order = _dependency_order(dependencies)

    subsystems = {}
    for name in order:
        table = declared[name]
        subsystems[name] = Subsystem(
            name=name,
            dependencies=dependencies[name],
            unprefixed_exports=tuple(table.get("unprefixed_exports", ())),
            directory=_directory(arch, name),
            public_includes=_public_includes(root, arch, name),
            third_party_headers=_third_party_headers(root, name, table),
        )
    return Declaration(root, subsystems, dict(entry_points))


def _directory(arch: str, name: str) -> str:
    if name == PORT:
        return f"{KERNEL_DIR}/{PORT}/{arch}"
    return f"{KERNEL_DIR}/{name}"


def _public_includes(root: Path, arch: str, name: str) -> tuple[str, ...]:
    if name == PORT:
        # The port interface, and the headers that the port gives it, which hold types and
        # constants only.
        candidates = [PORT_INTERFACE_DIR, f"{KERNEL_DIR}/{PORT}/{arch}/include"]
    else:
        candidates = [f"{KERNEL_DIR}/{name}/include"]
    return tuple(c for c in candidates if (root / c).is_dir())


def _third_party_headers(root: Path, name: str, table: dict[str, Any]) -> tuple[str, ...]:
    found = []
    for header in table.get("third_party_headers", ()):
        matches = sorted((root / THIRD_PARTY_DIR).glob(f"*/{header}"))
        if len(matches) != 1:
            raise DeclarationError(
                "unknown-third-party-header",
                f"{name} may include '{header}', which must be in exactly one directory under "
                f"{THIRD_PARTY_DIR}/ but is in {len(matches)}",
            )
        found.append(matches[0].relative_to(root).as_posix())
    return tuple(found)


def _check_disk(root: Path, arch: str, names: list[str]) -> None:
    """The declared subsystems and the directories under kernel/ must be the same set."""
    kernel = root / KERNEL_DIR
    on_disk = sorted(p.name for p in kernel.iterdir() if p.is_dir() and not p.name.startswith("."))
    for name in names:
        if name not in on_disk:
            raise DeclarationError(
                "missing-directory", f"{name} is declared but {KERNEL_DIR}/{name}/ doesn't exist"
            )
    for name in on_disk:
        if name not in names:
            raise DeclarationError(
                "undeclared-directory", f"{KERNEL_DIR}/{name}/ is a subsystem that isn't declared"
            )
    if PORT in names:
        if not (root / PORT_INTERFACE_DIR).is_dir():
            raise DeclarationError(
                "missing-port", f"the port interface {PORT_INTERFACE_DIR}/ doesn't exist"
            )
        if not (root / KERNEL_DIR / PORT / arch / PORT_FRAGMENT).is_file():
            raise DeclarationError(
                "missing-port",
                f"there is no port for {arch}: "
                f"{KERNEL_DIR}/{PORT}/{arch}/{PORT_FRAGMENT} doesn't exist",
            )


def _dependency_order(dependencies: dict[str, tuple[str, ...]]) -> list[str]:
    """Orders subsystems with dependencies first, and rejects unknown names and cycles."""
    for name, wanted in dependencies.items():
        for dependency in wanted:
            if dependency not in dependencies:
                raise DeclarationError(
                    "unknown-dependency", f"{name} depends on {dependency}, which isn't declared"
                )

    order: list[str] = []
    visiting: list[str] = []

    def visit(name: str) -> None:
        if name in order:
            return
        if name in visiting:
            cycle = [*visiting[visiting.index(name) :], name]
            raise DeclarationError("cyclic-dependency", " -> ".join(cycle))
        visiting.append(name)
        for dependency in sorted(dependencies[name]):
            visit(dependency)
        visiting.pop()
        order.append(name)

    for name in sorted(dependencies):
        visit(name)
    return order


def render_makefile(declaration: Declaration) -> str:
    """The declaration as make variables, which the build includes."""
    lines = [
        "# Generated by tools/subsystems.py from kernel/subsystems.toml. Don't edit it.",
        f"SUBSYSTEMS := {' '.join(declaration.subsystems)}",
        f"SUBSYSTEM_FILES := {' '.join(declaration.files())}",
    ]
    for name, subsystem in declaration.subsystems.items():
        includes = " ".join(f"-I{path}" for path in declaration.includes(name))
        lines += [
            f"{name}.dir := {subsystem.directory}",
            f"{name}.srcs := {' '.join(declaration.sources(name))}",
            f"{name}.includes := {includes}",
        ]
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("command", choices=["check", "makefile"])
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--arch", default="x86_64")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    try:
        declaration = load(args.root, args.arch)
    except DeclarationError as error:
        print(error, file=sys.stderr)
        return 1

    if args.command == "makefile":
        text = render_makefile(declaration)
        # Leave the file alone when nothing changed, so that make doesn't rebuild for nothing.
        if not args.output.exists() or args.output.read_text() != text:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
