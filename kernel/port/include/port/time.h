#ifndef PORT_TIME_H
#define PORT_TIME_H

#include <stdint.h>

/*
 * The port interface: time (ADR 0010). Every port provides these. NOVA_EXPORT comes from the
 * build's prelude (mk/prelude.h).
 */

/*
 * Monotonic nanoseconds since boot. It is 0 until the port has calibrated its clock, which it does
 * before it calls kmain, so it is live from kmain's first line.
 */
NOVA_EXPORT uint64_t port_clock_now(void);

#endif
