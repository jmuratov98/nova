#!/usr/bin/env python3
"""Checks the kernel's sources for what the compiler's include paths can't (ADR 0002, ADR 0003).

Portable code is everything under kernel/ except a port's own directory. It never tests an
architecture macro.

    check_sources.py [--arch ARCH]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import subsystems
from subsystems import Declaration

C_SUFFIXES = (".c", ".h")
SCANNED = (*C_SUFFIXES, ".S")

# The macros that name an architecture or one of its features.
ARCH_MACROS = re.compile(
    r"\b(__x86_64__|__x86_64|__amd64__|__amd64|__i386__|__i386|__aarch64__|__arm64__|__arm__|"
    r"__riscv|__riscv_xlen|_M_X64|_M_IX86|_M_ARM64)\b"
)
INLINE_ASM = re.compile(r"\b(asm|__asm__|__asm)\b")
INCLUDE = re.compile(r"^\s*#\s*include\s*([<\"])([^>\"]+)[>\"]")
# Directives that make a symbol global without the prelude's macros, whether in an assembly file or
# in the string of an inline asm. Only the prelude's own macros may use them.
RAW_GLOBAL = re.compile(r"(?:^|[\s\"';])(\.globl|\.global|\.weak)\b")


def spaces(text: str) -> str:
    return re.sub(r"[^\n]", " ", text)


def blank(text: str, quotes: str = "", hide: bool = False) -> str:
    """The text with every comment replaced by spaces, so that what's left keeps its line
    numbers. The characters in quotes begin literals, which are copied as they are, or, if hide
    is set, have their insides replaced by spaces too. Assembly, where a quote can be anything,
    passes no quotes."""
    out = []
    i = 0
    quote = ""
    while i < len(text):
        pair = text[i : i + 2]
        if quote:
            length = 2 if text[i] == "\\" else 1
            body = text[i : i + length]
            if text[i] == quote:
                quote = ""
            else:
                body = spaces(body) if hide else body
            out.append(body)
            i += length
        elif pair == "/*":
            end = text.find("*/", i + 2)
            end = len(text) if end < 0 else end + 2
            out.append(spaces(text[i:end]))
            i = end
        elif pair == "//":
            end = text.find("\n", i)
            end = len(text) if end < 0 else end
            out.append(spaces(text[i:end]))
            i = end
        else:
            if text[i] in quotes:
                quote = text[i]
            out.append(text[i])
            i += 1
    return "".join(out)


def is_portable(path: str) -> bool:
    parts = Path(path).parts
    in_a_port = len(parts) > 2 and parts[1] == subsystems.PORT and parts[2] != "include"
    return not in_a_port


def subsystem_of(path: str) -> str:
    return Path(path).parts[1]


def resolve(declaration: Declaration, path: str, quoted: bool, header: str) -> str | None:
    """Where the compiler finds an include of the file at path, or None if it doesn't."""
    searched = [str(Path(path).parent)] if quoted else []
    searched += declaration.includes(subsystem_of(path))
    for directory in searched:
        candidate = Path(directory) / header
        if (declaration.root / candidate).is_file():
            return candidate.as_posix()
    return None


def check_file(declaration: Declaration, path: str) -> list[str]:
    original = (declaration.root / path).read_text()
    is_c = path.endswith(C_SUFFIXES)
    quotes = "\"'" if is_c else ""
    code = blank(original, quotes, hide=True)
    errors = []
    for number, line in enumerate(blank(original, quotes).splitlines(), start=1):
        for match in RAW_GLOBAL.finditer(line):
            errors.append(
                f"{path}:{number}: error: raw-globl: '{match.group(1)}' declares a symbol "
                f"directly, so use NOVA_FUNC or NOVA_EXPORT_FUNC from mk/prelude.h, which make "
                f"it hidden unless it is exported"
            )
    for number, line in enumerate(blank(original, quotes).splitlines(), start=1):
        include = INCLUDE.match(line)
        if not include:
            continue
        spelled = f"{include[1]}{include[2]}{'>' if include[1] == '<' else include[1]}"
        header = Path(include[2])
        # The include paths are what keeps a subsystem to its dependencies' headers, and a path
        # that climbs out of the directory, or starts at the root, doesn't use them.
        if header.is_absolute() or ".." in header.parts:
            errors.append(
                f"{path}:{number}: error: include-escape: {subsystem_of(path)} includes {spelled}, "
                f"which names a header by a path outside the include paths"
            )
            continue
        # The port interface's headers are the only part of the port that portable code may
        # include.
        found = resolve(declaration, path, include[1] == '"', include[2])
        if subsystem_of(path) != subsystems.PORT and found and not is_portable(found):
            errors.append(
                f"{path}:{number}: error: port-private-include: {subsystem_of(path)} includes "
                f"{spelled}, which belongs to the port, and portable code includes only the port "
                f"interface's headers"
            )
    if is_portable(path):
        for number, line in enumerate(code.splitlines(), start=1):
            for match in ARCH_MACROS.finditer(line):
                errors.append(
                    f"{path}:{number}: error: arch-macro: '{match.group(1)}' is tested in "
                    f"portable code, which only a port may do"
                )
            for match in INLINE_ASM.finditer(line) if is_c else ():
                errors.append(
                    f"{path}:{number}: error: inline-asm: '{match.group(1)}' is used in "
                    f"portable code, which only a port may do"
                )
    return errors


def check(declaration: Declaration) -> list[str]:
    errors = []
    for path in declaration.files():
        if path.endswith(SCANNED):
            errors.extend(check_file(declaration, path))
    return errors


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--arch", default="x86_64")
    args = parser.parse_args(argv)

    try:
        declaration = subsystems.load(args.root, args.arch)
    except subsystems.DeclarationError as error:
        print(error, file=sys.stderr)
        return 1

    errors = check(declaration)
    for message in errors:
        print(message, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
