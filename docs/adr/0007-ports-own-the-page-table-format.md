# Ports own the page-table format behind address-space operations

Paging is split at the address space. Each port owns its page-table format entirely and offers the portable `mm` a few operations on an opaque address space: create, destroy, map one page, unmap, translate and activate. Flags are portable: read, write, execute, user, and normal or device memory. The port invalidates TLB entries itself, so a change is in effect when the call returns. It also makes the kernel half visible in every address space in its own way: x86-64 copies pre-allocated top-level entries, and AArch64 uses `TTBR1_EL1`. When the port needs a frame for a page table, it calls two new kernel-side entry points implemented by `mm`, `kframe_alloc` and `kframe_free`, and reaches the table through its own direct-map constant. The interface is shaped by what `mm` needs rather than by x86-64's four-level tree, so AArch64's split roots and RISC-V's Sv39 and Sv48 fit without changing portable code.

## Considered Options

- **A portable walker in `mm`**, with each port supplying level geometry and functions that encode and decode entries (Linux's approach): rejected because the portable side would have to know the tree's shape. AArch64's separate kernel root doesn't fit, and [ADR 0003](0003-subsystem-boundaries-enforced-by-include-paths-and-partial-linking.md) keeps architecture macros out of portable code.
- **Frame reserves passed into each map call**: rejected because every caller would have to size the reserve for each port's worst-case walk.

## Consequences

- The port interface's kernel-side entry points become five: kernel booted, interrupt arrived, system call arrived, log and panic, and frame allocation ([ADR 0002](0002-acyclic-subsystem-graph-and-port-interface.md), amended).
- The port maps its own devices, such as the LAPIC, into a port-reserved window with these same operations, so the port's MMIO needs no further interface.
- Large pages need a change to the port interface. In the First process tree, every mapping is one 4 KiB page.
