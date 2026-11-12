#ifndef PORT_CPU_H
#define PORT_CPU_H

/*
 * The port interface: CPU and power. Every port provides these. NOVA_EXPORT comes from the build's
 * prelude (mk/prelude.h).
 */

/* Masks interrupts on this CPU. */
NOVA_EXPORT void port_irq_disable(void);

#endif
