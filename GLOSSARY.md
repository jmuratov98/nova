# Nova

Nova is a POSIX operating system with a self-built kernel, made as a learning project held to serious engineering standards.

## Architecture

**Nova**:
The whole operating system: the kernel together with the userland that ships with it.
_Avoid_: NovaOS, the kernel (when meaning the whole system)

**Kernel**:
The privileged part of Nova: one image running in one address space.
_Avoid_: core, OS (when meaning only the privileged part)

**Modular monolith**:
Nova's kernel architecture: a single kernel image in a single address space, composed of subsystems whose boundaries are enforced at build time.
_Avoid_: modular-monolithic, hybrid kernel, microkernel

**Subsystem**:
A bounded part of the kernel, such as memory management, the scheduler or a filesystem, that the rest of the kernel may reach only through its declared interface.
_Avoid_: component, module (reserved for loadable modules)

**Export**:
A symbol a subsystem makes reachable from other subsystems. Everything a subsystem doesn't export is private to it.
_Avoid_: public symbol, API (when meaning a single symbol)

**Port**:
The subsystem that implements the port interface for one CPU architecture, as in "the x86-64 port".
_Avoid_: target, platform, arch

**Port interface**:
The two-sided contract between the portable kernel and every port: what each port provides, and the few entry points the portable kernel provides to ports.
_Avoid_: architecture interface

**Portable kernel**:
The kernel's subsystems other than the port, written once for every architecture.
_Avoid_: generic kernel, common code

**x86-64**:
The 64-bit x86 architecture. Written x86-64 in prose and `x86_64` in identifiers such as target triples and directory names.
_Avoid_: x86_64 (in prose), amd64, x64

**Loadable module**:
A subsystem packaged separately from the kernel image and attached to a running kernel.
_Avoid_: plugin, extension, driver (when meaning the packaging)

## Userland

**Userland**:
The part of Nova that runs in user mode: its programs and the code they link against.
_Avoid_: user space, userspace

**init**:
The first userland program the kernel starts. Every other process descends from it.
_Avoid_: PID 1 (when meaning the program), init process (when meaning the program)

**Bootstrap runtime**:
The minimal startup code, system-call wrappers and helpers that userland programs link against until a libc is ported.
_Avoid_: libc, mini-libc, crt0, rt (in prose)

## Delivery

**Milestone**:
A named state of Nova that can be tested, described by a spec in the repo, which the implementation works to reach.
_Avoid_: release, version, phase

**First process tree**:
Nova's first milestone: the kernel boots, loads `init` from the initial ramdisk, and `init` runs a child twice, once to exit and once to fault, reaping each and reporting how it ended.
_Avoid_: M1 (fine as shorthand in conversation, but not in specs), MVP, hello world

**Boot test**:
An automated test that boots the boot image in QEMU and judges the run by how QEMU exits and by the lines on the serial console.
_Avoid_: integration test, end-to-end test, smoke test, QEMU test

## Build

**Boot image**:
The bootable file the build produces, holding the bootloader, the kernel and the initial ramdisk.
_Avoid_: ISO, disk image, image (alone)

## Compatibility

**POSIX conformance**:
Nova's compatibility target: implementing the POSIX.1-2024 interfaces faithfully enough that unmodified POSIX software builds and runs. It does not mean formal certification.
_Avoid_: POSIX-compliant, POSIX-certified, POSIX-like

## System calls

**System call**:
A request from a userland program to the kernel. Written "system call" in prose and `syscall` in identifiers.
_Avoid_: syscall (in prose), kernel call, trap

**System-call interface**:
Nova's own set of system calls and the conventions for numbering and invoking them.
_Avoid_: syscall ABI, kernel API

## Memory

**Frame**:
A fixed-size, aligned block of physical memory, the unit in which the kernel hands out physical memory.
_Avoid_: page (when meaning physical memory), page frame

**Page**:
A fixed-size, aligned block of virtual memory in an address space, backed by one frame when mapped.
_Avoid_: frame (when meaning virtual memory)

**Address space**:
The virtual-to-physical mappings a program runs in: a user half of its own, plus the kernel half.
_Avoid_: page table (when meaning the whole), memory map, mm

**User half**:
The lower part of every address space, holding a program's own pages, which user mode may access.
_Avoid_: user space (when meaning the address range), lower half

**Kernel half**:
The upper part of every address space, holding the kernel. It is the same in every address space, and user mode can't access it.
_Avoid_: kernel space (when meaning the address range), higher half

**Region**:
A contiguous range of pages in an address space's user half, all with the same permissions, such as a program's stack.
_Avoid_: VMA, mapping, segment (reserved for ELF segments)

**Direct map**:
The kernel's mapping of all physical RAM at a fixed virtual offset in the kernel half, through which the kernel reaches any frame.
_Avoid_: HHDM (Limine's own map, used only during boot), physmap, identity map

**Kernel heap**:
The kernel's allocator for objects of any size, as opposed to whole frames.
_Avoid_: kmalloc (in prose), slab (when meaning the whole heap)
