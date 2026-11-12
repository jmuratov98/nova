#include "x86.h"
#include <port/entry.h>

/*
 * The port's start-up before kmain, which the entry stub runs on the boot stack. It does only work
 * on the CPU and through I/O ports, so it needs nothing from the portable kernel. The LAPIC, which
 * is memory-mapped, waits for port_init, after mm_init.
 *
 * The IDT loads second, so from there on a fault ends the run with the panic outcome instead of
 * triple-faulting. The clock is calibrated last, and is live from kmain's first line.
 */
noreturn void port_startup(void) {
    gdt_load();
    idt_load();
    cpu_setup();
    pic_mask();
    tsc_calibrate();
    kmain();
}
