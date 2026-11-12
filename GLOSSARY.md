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
Nova's first milestone: the kernel boots, loads `init` from the initial ramdisk, and `init` runs `/bin/echo`, then forks a child that exits with a status and one that faults, reaping each and reporting how it ended.
_Avoid_: M1 (fine as shorthand in conversation, but not in specs), MVP, hello world

**Boot test**:
An automated test that boots the boot image in QEMU and judges the run by how QEMU exits and by the lines on the serial console.
_Avoid_: integration test, end-to-end test, smoke test, QEMU test

**Host test**:
An automated test that builds one portable subsystem for the host, with fakes for its dependencies, and runs it without QEMU.
_Avoid_: unit test (alone), native test

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

## Files

**Initial ramdisk**:
The archive of userland programs that the bootloader loads alongside the kernel, and that the kernel mounts as its root.
_Avoid_: initrd, initramfs (the subsystem that reads it), ramdisk (alone)

**Vnode**:
The kernel's object for one file, directory or device, independent of the filesystem that holds it.
_Avoid_: inode, node, file (when meaning the object rather than an opening of it)

**Open file**:
One opening of a vnode, holding its offset and access mode, shared by every file descriptor that refers to it.
_Avoid_: file description, file object, file (alone)

## Executables

**Executable**:
The file a program is loaded from: an ELF file holding the program's segments and its entry point.
_Avoid_: binary, image (alone)

**Segment**:
A part of an executable, described by one ELF program header, that is placed in memory when the program is loaded.
_Avoid_: section, region (the address-space side)

**Initial stack**:
What a program finds at its stack pointer when it starts: its argument count, its arguments, its environment and its auxiliary vector.
_Avoid_: startup stack, auxv stack

## Interrupts and time

**Interrupt**:
An asynchronous event from a device or timer that makes the CPU stop what it's running.
_Avoid_: IRQ (in prose), exception

**Exception**:
A synchronous event caused by the instruction the CPU was executing, such as touching unmapped memory or dividing by zero.
_Avoid_: trap, interrupt

**Fault**:
An exception that reports an error in the code that was running, such as touching unmapped memory or executing an invalid instruction.
_Avoid_: crash, segfault (in prose)

**Interrupt line**:
A numbered input through which a device raises interrupts, independent of how the port routes it to the CPU.
_Avoid_: IRQ number, vector, GSI

**Tick**:
The periodic timer interrupt that drives preemption.
_Avoid_: jiffy, timer interrupt (when meaning the tick)

**Thread context**:
The kernel running on behalf of a thread, including while it handles a system call or an exception from that thread's program. Code in thread context may block.
_Avoid_: process context

**Interrupt context**:
The kernel handling an interrupt. Code in interrupt context can't block, and other interrupts wait until it's done.
_Avoid_: atomic context, IRQ context

## Console and log

**Console**:
The device through which Nova talks to whoever is watching it. The kernel log and init's standard input, output and error all go to it.
_Avoid_: terminal, TTY, serial port (when meaning the console)

**Kernel log**:
The kernel's account of what it is doing, made of whole lines, each stamped with the time since boot and the subsystem that wrote it.
_Avoid_: dmesg, printk, kernel messages

**Log sink**:
An output that the kernel log writes its lines to, such as the console.
_Avoid_: backend, appender, log device

**Panic**:
The kernel stopping itself when it finds it can't safely go on: it reports why on every log sink and powers off with the panic outcome.
_Avoid_: crash, oops, halt (when meaning the whole sequence)

## Threads

**Thread**:
The unit of execution the scheduler runs, with a kernel stack of its own. A process runs its program on a thread, but the scheduler knows only threads.
_Avoid_: task, kthread, process (when meaning what the scheduler runs)

**Context switch**:
Handing the CPU from one thread to another, saving the first one's registers and restoring the second one's.
_Avoid_: task switch (x86-64's hardware task switching is something else), reschedule

**Run queue**:
The threads that are ready to run but aren't running.
_Avoid_: ready list, ready queue

**Wait queue**:
The threads blocked until a particular condition may have changed, such as a child exiting.
_Avoid_: sleep channel, wait channel

**Idle thread**:
The thread the scheduler runs when no other thread is ready. It's never on the run queue.
_Avoid_: idle task, idle process, swapper

## Processes

**Process**:
A program running in its own address space, with its own file descriptors and its place in the process tree. Each process runs on exactly one thread.
_Avoid_: task, job, program (when meaning the running instance)

**PID**:
The number that identifies a process from its creation until its parent reaps it.
_Avoid_: process ID (in identifiers), task ID

**Process tree**:
The parent and child relationships among processes. init is at the root, and every other process has a parent.
_Avoid_: process hierarchy

**Orphan**:
A process whose parent has ended. init adopts it.
_Avoid_: abandoned process

**Zombie**:
A process that has ended but hasn't been reaped yet. It keeps only its PID and its wait status.
_Avoid_: defunct process, dead process

**Reap**:
For a parent to collect a zombie child's wait status, which ends the child for good and frees its PID.
_Avoid_: collect, join, wait for (when meaning the collection itself)

**Wait status**:
How a process ended, as its parent learns it: either the exit status it passed to `_exit`, or the signal it was killed by.
_Avoid_: exit code (when the process was killed), return code

**File descriptor**:
A small number by which a process refers to one of its open files.
_Avoid_: fd (in prose), handle

**Process name**:
A short label for a process in the kernel log, taken from the last program it executed.
_Avoid_: comm, command name
