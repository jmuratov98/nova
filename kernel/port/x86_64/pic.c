#include <stdint.h>

#include "x86.h"

/*
 * The 8259 PICs. Limine masks them but leaves them where the BIOS put them, which sends IRQ 0 to
 * #DF's vector. The port remaps them to 0x20-0x2f, clear of the exceptions, and masks every line.
 * Nova takes its interrupts from the LAPIC, so only a spurious IRQ 7 or 15 can still arrive.
 */

#define PIC1_COMMAND 0x20
#define PIC1_DATA 0x21
#define PIC2_COMMAND 0xa0
#define PIC2_DATA 0xa1

#define ICW1_INIT 0x11 /* initialise, cascaded, ICW4 follows */
#define ICW4_8086 0x01 /* 8086 mode */
#define PIC1_VECTOR 0x20
#define PIC2_VECTOR 0x28
#define PIC1_CASCADE 0x04 /* PIC2 is on PIC1's line 2 */
#define PIC2_CASCADE 0x02 /* PIC2's cascade identity */
#define MASK_ALL 0xff

/* A write to an unused port, which gives an old PIC time to take the last one. */
static void io_wait(void) { outb(0x80, 0); }

static void pic_write(uint16_t port, uint8_t value) {
    outb(port, value);
    io_wait();
}

void pic_mask(void) {
    pic_write(PIC1_COMMAND, ICW1_INIT);
    pic_write(PIC2_COMMAND, ICW1_INIT);
    pic_write(PIC1_DATA, PIC1_VECTOR);
    pic_write(PIC2_DATA, PIC2_VECTOR);
    pic_write(PIC1_DATA, PIC1_CASCADE);
    pic_write(PIC2_DATA, PIC2_CASCADE);
    pic_write(PIC1_DATA, ICW4_8086);
    pic_write(PIC2_DATA, ICW4_8086);
    pic_write(PIC1_DATA, MASK_ALL);
    pic_write(PIC2_DATA, MASK_ALL);
}
