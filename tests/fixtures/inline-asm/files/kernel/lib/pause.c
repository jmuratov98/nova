void lib_pause(void);

void lib_pause(void) { __asm__ volatile("nop"); }
