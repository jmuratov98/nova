# Every lock masks interrupts

`sync` exports one kind of lock, a spinlock that masks interrupts on its CPU for as long as it's held, and every lock in the kernel is one of these. On one CPU, masking keeps the tick out, so no thread can be switched away while it holds a lock, even if the kernel later becomes preemptible. On SMP, the lock's atomic flag also keeps other CPUs out. Every lock is then safe to take from interrupt context, and no lock site has to work out whether an interrupt handler can reach it. Masking nests through a per-CPU depth count, so locks may be released in any order. A lock records the CPU that holds it, not the thread, so `sched` can hand its lock across a context switch.

## Considered Options

- **A masking and a non-masking spinlock** (Linux's `spin_lock_irqsave` and `spin_lock`), with the non-masking one for locks taken only in thread context, such as `mm`'s and `proc`'s: rejected. [ADR 0011](0011-the-tick-preempts-only-user-mode.md) says locks are written as though threads could interleave anywhere. Under a preemptible kernel, a thread preempted while holding a non-masking spinlock leaves the next thread on that CPU spinning forever, unless every lock maintains the preempt count that ADR 0011 rejected.
- **A masking spinlock plus a sleeping mutex** for long sections taken only in thread context: deferred. A mutex blocks, so it needs `sched`, but `sync` sits below `sched` in the subsystem graph, and `sched_wait` would have to accept both kinds. It becomes worth having when SMP makes long spinning hold times costly.

## Consequences

- Interrupts stay masked for as long as any lock is held: across a console `write`, and across `fork`'s eager copy under the process lock. A tick can be late, and `time` catches up on missed deadlines.
- `sched_wait(wq, lock)` blocks only when the caller's lock is its only masking and interrupts were enabled outside it. That one check also refuses blocking in interrupt context or inside a bare masking section.
- On one CPU, any lock found held is held by this CPU, so taking it again is the only possible deadlock, and `sync` panics on it. Lock order matters only once there's SMP.
