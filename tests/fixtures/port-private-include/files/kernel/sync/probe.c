#include <port/x86_64/regs.h>

int sync_regs(void);

int sync_regs(void) { return PORT_X86_64_REGS; }
