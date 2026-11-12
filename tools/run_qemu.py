#!/usr/bin/env python3
"""Runs QEMU in the foreground, then says in one line how the run ended.

`make run` and `make debug` use this. QEMU keeps the terminal, for the serial console and the
monitor, and when it exits its status is read as an outcome (tools/outcome.py). This exits 0 only
when init exited 0, so that make doesn't report the status that stands for success as an error.

    run_qemu.py --qemu QEMU --outcomes '33 35 37' -- QEMU-ARGUMENT...
"""

from __future__ import annotations

import argparse
import re
import shlex
import shutil
import subprocess
import sys

import outcome

# The oldest QEMU that Nova runs on. 10.2 is the first with -run-with exit-with-parent, which the
# boot test uses, and the version that CI's Ubuntu ships.
MINIMUM_VERSION = (10, 2)


def version_problem(qemu: list[str]) -> str | None:
    """Why this QEMU can't be used, or None if it can."""
    if shutil.which(qemu[0]) is None:
        return f"{qemu[0]} is needed to run Nova, but it was not found. See docs/building.md"
    probe = subprocess.run([*qemu, "--version"], check=False, capture_output=True, text=True)
    found = probe.stdout
    match = re.search(r"version (\d+)\.(\d+)", found)
    if match is None:
        return f"couldn't read the version of {qemu[0]} from {found.strip()!r}"
    version = (int(match[1]), int(match[2]))
    if version < MINIMUM_VERSION:
        wanted = ".".join(map(str, MINIMUM_VERSION))
        return f"QEMU {wanted} or newer is required, but {qemu[0]} is {match[1]}.{match[2]}"
    return None


def run(command: list[str]) -> int:
    """Runs QEMU and waits for it. A Ctrl-C that reaches this process too (when the terminal isn't
    QEMU's) is QEMU's to act on, so this keeps waiting and reports how QEMU ended."""
    process = subprocess.Popen(command)
    while True:
        try:
            return process.wait()
        except KeyboardInterrupt:
            continue


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--qemu", required=True, help="the QEMU to run, as a command")
    parser.add_argument("--outcomes", required=True, help="the port's exit status per outcome")
    parser.add_argument("arguments", nargs="*", help="QEMU's arguments, after --")
    args = parser.parse_args(argv)

    qemu = shlex.split(args.qemu)
    problem = version_problem(qemu)
    if problem is not None:
        print(problem, file=sys.stderr)
        return 1

    ending = outcome.read(run([*qemu, *args.arguments]), outcome.parse_statuses(args.outcomes))
    if sys.stdout.isatty():
        # UEFI's console leaves the cursor at the top of the screen, where the line would overwrite
        # the firmware's own, so it goes on a fresh line at the bottom instead.
        sys.stdout.write("\x1b[999;1H\n")
    print(ending.description)
    return 0 if ending.succeeded else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
