# Ports report interrupts and exceptions to `irq` as portable events

The port decodes every interrupt and exception before the portable kernel sees it, and calls *interrupt arrived* with a portable event of one of three kinds: the timer, a device's interrupt line, or an exception. An exception carries a portable fault kind (memory, alignment, illegal instruction, arithmetic or breakpoint), the faulting address if there is one, the program counter, whether it came from user mode, and an opaque pointer to the saved registers that only the port can read. `irq` never sees an x86-64 vector, a GIC INTID or RISC-V's `scause`. It panics on a fault from the kernel and passes a fault from user mode to a hook that `proc` fills. `proc` alone maps a fault kind to a signal, so signal numbers stay out of the port interface. The port acknowledges the interrupt controller before it calls *interrupt arrived*, and saves the whole interrupted state on the current thread's kernel stack, so a handler may switch threads and the interrupted one resumes exactly where it stopped. Spurious interrupts never leave the port, and double faults, NMIs and machine checks panic from the port directly, on stacks of their own.

## Considered Options

- **Raw vector numbers passed to `irq`**: rejected because x86-64's numbering would sit in portable code, which [ADR 0003](0003-subsystem-boundaries-enforced-by-include-paths-and-partial-linking.md) rules out, and each port numbers its interrupts differently.
- **One entry point per kind**: rejected because it grows the port interface's kernel-side entry points without carrying anything the event's kind doesn't.
- **Acknowledging after the handler, forbidding handlers to switch threads, and switching in a "returning to user mode" entry point** (Linux's need-reschedule flag): rejected because it needs a sixth kernel-side entry point, and a handler that may switch can carry out the same policy without one.
- **The port choosing the signal**: rejected because every port would then carry the system-call interface's signal numbers.

## Consequences

- A fault from user mode is handled in thread context, as the thread that faulted, so `proc` can end the process the way `_exit` does, and its hook never returns.
- The tick's handler is told whether it interrupted user mode, so the scheduler can tell when switching is always safe.
- When device lines arrive, the interrupt is already acknowledged when its handler runs, so a level-triggered line has to be serviced or masked before its handler lets another thread run.
