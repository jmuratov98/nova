# Ports provide a one-shot timer and a clock, and `time` makes the tick

Each port provides a monotonic clock, `port_clock_now()`, in nanoseconds since boot, and a one-shot timer, `port_timer_arm(deadline)`, whose interrupt reaches `irq` only at or after the deadline. If the hardware fires early, the port re-arms and swallows the interrupt. `time` makes the preemption tick by re-arming at absolute deadlines one period apart, so the tick doesn't drift, and it skips ticks a stalled host missed instead of replaying them. AArch64's generic timer and RISC-V's `time` CSR with SBI `set_timer` have exactly this shape and no periodic mode. Sleeping, timeouts and `clock_gettime(CLOCK_MONOTONIC)` need the same two operations, so the port interface won't change when they arrive. On x86-64 the clock is the TSC and the timer is the LAPIC timer in one-shot mode. QEMU's `qemu64` CPU offers no TSC-deadline mode, no invariant TSC and no frequency leaves, so the port calibrates both against PIT channel 2 at boot.

## Considered Options

- **A periodic port timer** (`port_timer_start(period)`): rejected. It's the simplest choice on x86-64 (LAPIC periodic mode, no clock), but the only clock would be a tick count with 10 ms resolution, the other two ports would have to emulate periodic mode, and the interface would change as soon as anything sleeps or reads the time.
- **The HPET or the ACPI PM timer as x86-64's clock**: rejected because both are found through ACPI tables, which nothing else in the First process tree parses. HPET reads are MMIO, and the PM timer is 24-bit, so it wraps every 4.7 s.

## Consequences

- The x86-64 port calibrates the TSC as well as the LAPIC timer, and logs both measured rates at boot so a bad calibration shows in the serial log.
- Under QEMU's TCG the guest TSC runs at about 1 GHz in 1 µs steps on an Apple M4 host, and at the host's own TSC rate on an x86-64 Linux host, so nothing may assume a TSC frequency.
- A tickless scheduler would need no change to the port interface.
