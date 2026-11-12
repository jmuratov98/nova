void port_irq_disable(void);
void lib_reach(void);

void lib_reach(void) { port_irq_disable(); }
