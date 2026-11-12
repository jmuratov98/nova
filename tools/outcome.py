"""How a run of Nova ended, read from QEMU's exit status (ADR 0006).

When init exits, or the kernel panics, the kernel powers off with an outcome, and the port hands
it to QEMU so that QEMU exits with a status that stands for it. Which status stands for which
outcome is the port's to say, in its port.mk (PORT_QEMU_OUTCOMES). Any other status means that the
kernel reported no outcome. In particular, QEMU exiting with 0 never means success: under
-no-reboot a reset or a triple fault exits with 0, and so does quitting from QEMU's monitor.
"""

from __future__ import annotations

from dataclasses import dataclass

# The outcomes, in the order that a port lists its exit statuses.
OUTCOMES = ("init exited 0", "init exited non-zero", "panic")


@dataclass(frozen=True)
class Ending:
    """How one run ended. outcome is None when the kernel reported none."""

    status: int  # QEMU's exit status, or minus the signal that killed it
    outcome: str | None
    description: str  # one line for a person

    @property
    def succeeded(self) -> bool:
        return self.outcome == OUTCOMES[0]


def parse_statuses(text: str) -> tuple[int, ...]:
    """The port's exit statuses, one per outcome, separated by spaces or commas."""
    statuses = tuple(int(word) for word in text.replace(",", " ").split())
    if len(statuses) != len(OUTCOMES):
        raise ValueError(f"expected {len(OUTCOMES)} exit statuses, one per outcome, not {text!r}")
    return statuses


def read(status: int, statuses: tuple[int, ...]) -> Ending:
    """The ending that QEMU's exit status stands for, given the port's statuses."""
    if status in statuses:
        outcome = OUTCOMES[statuses.index(status)]
        return Ending(status, outcome, f"outcome: {outcome} (QEMU exited with {status})")
    if status < 0:
        return Ending(status, None, f"no outcome: QEMU was killed by signal {-status}")
    if status == 0:
        why = "the machine reset or triple-faulted, or QEMU was quit"
    elif status == 1:
        why = "QEMU stopped with an error"
    else:
        why = "the port reports no outcome with that status"
    return Ending(status, None, f"no outcome: {why} (QEMU exited with {status})")
