# The kernel's subsystems form an acyclic graph, and ports sit behind a two-sided port interface

The kernel is split into coarse, flat subsystems, roughly one per major job, and their allowed dependencies form a declared, acyclic graph. The graph isn't strictly layered. Where two subsystems need each other, the lower one declares a hook and the higher one fills it in at runtime, which counts as a dependency of the higher on the lower. Architecture-specific code is one subsystem per architecture, the port, behind a two-sided port interface. One side is what every port provides. The other is a few entry points the portable kernel provides to ports (kernel booted, interrupt arrived, system call arrived, log and panic), each implemented by exactly one subsystem. A port never names a portable subsystem. Three ports are planned, and the two-sided contract makes "what does a port have to do?" a single document, which keeps the second and third ports affordable.

## Considered Options

- **Linux-style `arch/` code that may call anything**: rejected because cycles form everywhere and nothing states what a port must provide.
- **Architecture code split across subsystems**, each with its own per-architecture parts: rejected because every new port would touch every subsystem.
- **Strict layers**: rejected because they force placements that don't reflect real relationships.
- **Allowing cycles**: rejected because a boundary that can be crossed in both directions means nothing.
- **Fine-grained subsystems**, such as a frame allocator separate from `mm`: rejected while the design is still being learned, because every boundary is an interface to maintain.

## Consequences

- The scheduler knows only threads, never processes.
- Limine is confined to `boot`, the only subsystem that includes `limine.h`.
- `lib` depends on nothing, not even the port interface, so it builds on the host.
- Start-up is explicit: `start` calls each subsystem's initialisation in a written-out order, with no initcalls.
