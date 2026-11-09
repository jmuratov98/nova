# When init exits, Nova powers off, and a boot test reads the outcome from QEMU's exit code

When `init` exits, the kernel logs its exit status and asks the port to power off with one of three outcomes: init exited 0, init exited non-zero, or the kernel panicked. `init` judges the run itself. It checks every call's result and how each child ended, and exits 0 only if all of it matched. A boot test passes only when QEMU exits with the "init exited 0" outcome and every expected line has appeared on the serial console, in order. On x86-64 the port writes `0x10`, `0x11` or `0x12` to QEMU's `isa-debug-exit` device at port `0xf4`, so QEMU exits with 33, 35 or 37. On a machine without that device, the port halts.

## Considered Options

- **Panic when init exits, as Linux does**: rejected because a passing run would then have no ending of its own. The harness would have to spot success in the serial output and kill QEMU.
- **init never exits, and the harness kills QEMU after the report**: rejected for the same reason.
- **The exit code alone**: rejected because a console that drops output could still pass.
- **The serial lines alone**: rejected because they can't tell a clean finish from a panic or a hang that comes after the last expected line.

## Consequences

- An exit status of 0 from QEMU never means success. `isa-debug-exit` statuses are always odd, and under `-no-reboot` a triple fault exits with 0.
- Every port has to provide a power-off that takes an outcome, so the AArch64 and RISC-V ports will need their own way to hand QEMU a status.
- `make run` boots the same machine as the boot test, so it also ends when `init` exits.
