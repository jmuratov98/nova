#include <stdint.h>

#include "x86.h"

/*
 * The GDT and the TSS. Limine's GDT is in memory the kernel will reclaim, and has no TSS, so the
 * port loads its own: null, kernel code and data, user data and user code (in the order that
 * SYSCALL and SYSRET require), and a TSS.
 *
 * The TSS gives #DF, NMI and #MC a 4 KiB stack each, so that they run on a known-good stack even
 * when the kernel stack has overflowed onto its guard page. RSP0, the stack for an interrupt from
 * user mode, stays unset until the first thread switch.
 */

#define IST_STACK_SIZE 4096

/* The TSS, as the CPU reads it in long mode. */
struct tss {
    uint32_t reserved0;
    uint64_t rsp[3];
    uint64_t reserved1;
    uint64_t ist[7];
    uint64_t reserved2;
    uint16_t reserved3;
    uint16_t iomap_base;
} __attribute__((packed));

_Static_assert(sizeof(struct tss) == 104, "the TSS is 104 bytes");

/* Code and data descriptors: base 0 and a 4 GiB limit, which long mode ignores but for L. */
#define KERNEL_CODE 0x00af9a000000ffffULL /* present, ring 0, execute/read, 64-bit */
#define KERNEL_DATA 0x00cf92000000ffffULL /* present, ring 0, read/write */
#define USER_DATA 0x00cff2000000ffffULL   /* present, ring 3, read/write */
#define USER_CODE 0x00affa000000ffffULL   /* present, ring 3, execute/read, 64-bit */
#define TSS_PRESENT_AVAILABLE 0x89ULL     /* present, type 9 (an available 64-bit TSS) */

/* The TSS descriptor takes two slots, filled in at run time, since they hold its address. */
static uint64_t gdt[7] __attribute__((aligned(16))) = {
    [KERNEL_CODE_SELECTOR / 8] = KERNEL_CODE,
    [KERNEL_DATA_SELECTOR / 8] = KERNEL_DATA,
    [USER_DATA_SELECTOR / 8] = USER_DATA,
    [USER_CODE_SELECTOR / 8] = USER_CODE,
};

static struct tss tss;
static uint8_t ist_stacks[3][IST_STACK_SIZE] __attribute__((aligned(16)));

void gdt_load(void) {
    tss.ist[IST_DOUBLE_FAULT - 1] = (uintptr_t)ist_stacks[0] + IST_STACK_SIZE;
    tss.ist[IST_NMI - 1] = (uintptr_t)ist_stacks[1] + IST_STACK_SIZE;
    tss.ist[IST_MACHINE_CHECK - 1] = (uintptr_t)ist_stacks[2] + IST_STACK_SIZE;
    tss.iomap_base = sizeof(tss); /* no I/O permission bitmap */

    uint64_t base = (uintptr_t)&tss;
    uint64_t limit = sizeof(tss) - 1;
    gdt[TSS_SELECTOR / 8] = (limit & 0xffffU) | ((base & 0xffffffU) << 16U) |
                            (TSS_PRESENT_AVAILABLE << 40U) | (((base >> 24U) & 0xffU) << 56U);
    gdt[TSS_SELECTOR / 8 + 1] = base >> 32U;

    struct descriptor_pointer pointer = {sizeof(gdt) - 1, (uintptr_t)gdt};
    __asm__ volatile("lgdt %0" : : "m"(pointer));

    /* A far return reloads CS. Data segments take the kernel's data selector, FS and GS null. */
    __asm__ volatile(
        "pushq %[code]\n\t"
        "leaq 1f(%%rip), %%rax\n\t"
        "pushq %%rax\n\t"
        "lretq\n"
        "1:\n\t"
        "movw %w[data], %%ds\n\t"
        "movw %w[data], %%es\n\t"
        "movw %w[data], %%ss\n\t"
        "movw %w[null], %%fs\n\t"
        "movw %w[null], %%gs"
        :
        : [code] "i"(KERNEL_CODE_SELECTOR), [data] "r"(KERNEL_DATA_SELECTOR), [null] "r"(0)
        : "rax", "memory");

    __asm__ volatile("ltr %w0" : : "r"(TSS_SELECTOR));
}
