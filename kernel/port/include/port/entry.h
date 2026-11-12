#ifndef PORT_ENTRY_H
#define PORT_ENTRY_H

#include <stdnoreturn.h>

/*
 * The port interface: the entry points that the portable kernel gives every port, and the only
 * symbols of the portable kernel that a port may reference. They carry a neutral k prefix instead
 * of their subsystem's, so a port never names a subsystem. kernel/subsystems.toml says which
 * subsystem implements each.
 */

/*
 * The kernel booted. The port calls this exactly once, when its own start-up is done, on the boot
 * stack, with interrupts masked. Implemented by start.
 */
NOVA_EXPORT noreturn void kmain(void);

#endif
