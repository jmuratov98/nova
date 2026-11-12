#include <port/cpu.h>

void port_irq_disable(void) { __asm__ volatile("cli" ::: "memory"); }
