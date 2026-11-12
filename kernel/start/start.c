#include <port/cpu.h>
#include <port/entry.h>

/*
 * The kernel's start-up, which the port calls once its own is done. There is nothing to start
 * yet, so the kernel powers off at once with the outcome for init exiting 0. That stands in for
 * init until it exists.
 */
noreturn void kmain(void) { port_power_off(PORT_OUTCOME_INIT_SUCCEEDED); }
