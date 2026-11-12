#ifndef PORT_CPU_H
#define PORT_CPU_H

#include <stdnoreturn.h>

/*
 * The port interface: CPU and power. Every port provides these. NOVA_EXPORT comes from the build's
 * prelude (mk/prelude.h).
 */

/* How a run of Nova ended, which the kernel hands the port when it powers off (ADR 0006). */
enum port_outcome {
    PORT_OUTCOME_INIT_SUCCEEDED, /* init exited 0 */
    PORT_OUTCOME_INIT_FAILED,    /* init exited non-zero, or was killed */
    PORT_OUTCOME_PANIC,          /* the kernel panicked */
};

/* Masks interrupts on this CPU. */
NOVA_EXPORT void port_irq_disable(void);

/*
 * Ends the run with an outcome, which the machine reports to whoever started it. Interrupts are
 * masked first. On a machine with no way to report an outcome, this halts forever.
 */
NOVA_EXPORT noreturn void port_power_off(enum port_outcome outcome);

#endif
