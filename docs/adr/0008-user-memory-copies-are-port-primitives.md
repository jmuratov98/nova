# User-memory copies are port primitives that recover from faults

The portable kernel never reads or writes user memory directly. User addresses travel as an opaque `mm_uptr_t` that can't be dereferenced. `mm`'s copy functions check that a range lies in the user half, then call port primitives to copy in, copy out, or copy in a NUL-terminated string. Each primitive opens the CPU's user-access guard for the duration of the copy (SMAP on x86-64, PAN on AArch64, `sstatus.SUM` on RISC-V). It recovers from a fault through a fixup table the port keeps itself, which the port's exception entry checks before calling *interrupt arrived*. A bad pointer therefore becomes `EFAULT`, and never a panic. Every port has to toggle the guard around each user access anyway, so the copy itself costs nothing extra in the port. It also keeps working unchanged when demand paging or copy-on-write arrives.

## Considered Options

- **Checking the range against the address space's regions, then using `memcpy`**: rejected because it's only sound while nothing can change mappings under the copy (no demand paging, no copy-on-write, no shared address spaces), and each port would still need the guard toggled.
- **A portable fixup table consulted by an `mm` page-fault handler**: rejected because it needs the faulting instruction's address and assembly copy loops in portable code, which [ADR 0003](0003-subsystem-boundaries-enforced-by-include-paths-and-partial-linking.md) rules out.

## Consequences

- `mm` registers no page-fault handler. The `mm` → `irq` arrow in [ADR 0002](0002-acyclic-subsystem-graph-and-port-interface.md)'s graph survives only if `fork` uses copy-on-write.
- Once demand paging exists, the port's fault path has to give `mm` a chance to resolve a fault before it applies a fixup.
