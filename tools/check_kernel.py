#!/usr/bin/env python3
"""Checks the linked kernel image for what the linker only warns about.

A kernel that links isn't necessarily one that a bootloader can start. When the linker script's
ENTRY names a symbol that the link can't see, which happens if the symbol isn't exported, lld
warns and writes an entry point of 0.

    check_kernel.py --nm NM --machine N --entry SYMBOL IMAGE
"""

from __future__ import annotations

import argparse
import shlex
import struct
import subprocess
import sys
from pathlib import Path

ELF_MAGIC = b"\x7fELF"
ET_EXEC = 2


def symbol_address(nm: list[str], image: Path, symbol: str) -> int | None:
    output = subprocess.run([*nm, str(image)], capture_output=True, text=True, check=True).stdout
    for line in output.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[2] == symbol:
            return int(parts[0], 16)
    return None


def check(image: Path, nm: list[str], machine: int, entry: str) -> list[str]:
    header = image.read_bytes()[:32]
    if header[:4] != ELF_MAGIC:
        return [f"{image.name}: error: kernel-image: not an ELF file"]
    kind, found_machine = struct.unpack_from("<HH", header, 16)
    (address,) = struct.unpack_from("<Q", header, 24)

    errors = []
    if kind != ET_EXEC:
        errors.append(f"{image.name}: error: kernel-image: the type is {kind}, not an executable")
    if found_machine != machine:
        errors.append(
            f"{image.name}: error: kernel-image: the machine is {found_machine}, not {machine}"
        )
    expected = symbol_address(nm, image, entry)
    if expected is None:
        errors.append(f"{image.name}: error: kernel-image: the entry point {entry} isn't defined")
    elif address != expected:
        errors.append(
            f"{image.name}: error: kernel-image: the entry point is {address:#x}, but {entry} is "
            f"at {expected:#x}, so the linker script's ENTRY can't find it"
        )
    return errors


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--nm", default="llvm-nm")
    parser.add_argument("--machine", type=int, required=True, help="the port's ELF machine number")
    parser.add_argument("--entry", required=True, help="the symbol that the entry point must be")
    parser.add_argument("image", type=Path)
    args = parser.parse_args(argv)

    errors = check(args.image, shlex.split(args.nm), args.machine, args.entry)
    for error in errors:
        print(error, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
