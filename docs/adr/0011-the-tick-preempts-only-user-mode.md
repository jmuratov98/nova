# The tick preempts a thread only when it interrupted user mode

`sched` switches threads from the tick only when the tick interrupted user mode. Kernel code runs until it blocks, exits or returns to user mode, so on one CPU another thread can cut into kernel code only at that code's own blocking points. The kernel's paths in the First process tree are short, [ADR 0009](0009-ports-report-interrupts-and-exceptions-as-portable-events.md) already tells the tick's handler whether it interrupted user mode, and a kernel that isn't preempted removes a class of races while the kernel is still being learned. Locks are still written as though threads could interleave anywhere, so adding SMP or kernel preemption later doesn't mean auditing every critical section.

## Considered Options

- **A preemptible kernel with a preempt count** (Linux): the tick may switch anywhere in thread context unless a lock or masking section has disabled preemption. Rejected for now, because every lock and masking section would have to maintain the count, and its races are hard to find in a kernel whose boot test runs two tiny programs.

## Consequences

- A long kernel path delays every other thread until it blocks or returns to user mode. A slice that runs out in the kernel isn't made up later: the next tick that lands in user mode switches.
- The idle thread runs in kernel mode, so the tick never preempts it. It checks the run queue itself each time it wakes from halting.
- Nothing may rely on the kernel being non-preemptible for its correctness. The "Concurrency on one CPU" design writes locks as though threads could interleave anywhere.
