#include "../port/include/port/cpu.h"

void lib_reach(void);

void lib_reach(void) { port_irq_disable(); }
