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
Nova's support for one CPU architecture, as in "the x86-64 port".
_Avoid_: target, platform, arch

**x86-64**:
The 64-bit x86 architecture. Written x86-64 in prose and `x86_64` in identifiers such as target triples and directory names.
_Avoid_: x86_64 (in prose), amd64, x64

**Loadable module**:
A subsystem packaged separately from the kernel image and attached to a running kernel.
_Avoid_: plugin, extension, driver (when meaning the packaging)

## Delivery

**Milestone**:
A named state of Nova that can be tested, described by a spec in the repo, which the implementation works to reach.
_Avoid_: release, version, phase

**First process tree**:
Nova's first milestone: the kernel boots, loads `init` from the initial ramdisk, and `init` starts a child process, reaps it and reports its exit status.
_Avoid_: M1 (fine as shorthand in conversation, but not in specs), MVP, hello world

## Compatibility

**POSIX conformance**:
Nova's compatibility target: implementing the POSIX.1-2024 interfaces faithfully enough that unmodified POSIX software builds and runs. It does not mean formal certification.
_Avoid_: POSIX-compliant, POSIX-certified, POSIX-like
