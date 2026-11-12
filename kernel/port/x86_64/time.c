#include <stdint.h>

#include "x86.h"
#include <port/time.h>

/*
 * The clock: the TSC, counted from when it was calibrated. qemu64 offers no invariant TSC and no
 * frequency leaves, and under QEMU's TCG the guest TSC runs at about 1 GHz on an Apple M4 and at
 * the host's own rate on an x86-64 host, so the rate is measured, once, against PIT channel 2 over
 * one 50 ms window. That is all I/O-port work, so it happens before kmain.
 */

#define PIT_HZ 1193182U
#define PIT_WINDOW_TICKS (PIT_HZ / 20U) /* 50 ms */
#define PIT_CHANNEL2_DATA 0x42
#define PIT_COMMAND 0x43
#define PIT_CHANNEL2_ONESHOT 0xb0 /* channel 2, low then high byte, mode 0, binary */

/* Port 0x61 holds channel 2's gate and output, and the speaker's enable. */
#define SYSTEM_CONTROL 0x61
#define CHANNEL2_GATE 0x01U
#define SPEAKER_ENABLE 0x02U
#define CHANNEL2_OUTPUT 0x20U

#define NS_PER_SECOND 1000000000ULL

static uint64_t tsc_hz;
static uint64_t tsc_start;

void tsc_calibrate(void) {
    uint8_t control = inb(SYSTEM_CONTROL);
    outb(SYSTEM_CONTROL, (uint8_t)((control & ~SPEAKER_ENABLE) | CHANNEL2_GATE));

    /* In mode 0 the output goes low now, and high again when the count reaches 0. */
    outb(PIT_COMMAND, PIT_CHANNEL2_ONESHOT);
    outb(PIT_CHANNEL2_DATA, PIT_WINDOW_TICKS & 0xffU);
    outb(PIT_CHANNEL2_DATA, PIT_WINDOW_TICKS >> 8U);
    uint64_t start = rdtsc();
    while ((inb(SYSTEM_CONTROL) & CHANNEL2_OUTPUT) == 0) {
    }
    uint64_t end = rdtsc();

    outb(SYSTEM_CONTROL, control);
    tsc_start = start;
    tsc_hz = (end - start) * PIT_HZ / PIT_WINDOW_TICKS;
}

/* In whole seconds and the rest, so that nothing overflows for a TSC of up to 18 GHz. */
uint64_t port_clock_now(void) {
    if (tsc_hz == 0) {
        return 0;
    }
    uint64_t ticks = rdtsc() - tsc_start;
    return ticks / tsc_hz * NS_PER_SECOND + ticks % tsc_hz * NS_PER_SECOND / tsc_hz;
}
