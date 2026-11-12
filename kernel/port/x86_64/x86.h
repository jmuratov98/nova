#ifndef X86_H
#define X86_H

/*
 * What the x86-64 port's own files share: the GDT's selectors, the start-up steps that run before
 * kmain, and wrappers for the instructions that C can't express. Only the port includes this. Its
 * constants come first, and assembly includes it for those.
 */

/* The GDT's selectors (gdt.c). User selectors are used with RPL 3. */
#define KERNEL_CODE_SELECTOR 0x08
#define KERNEL_DATA_SELECTOR 0x10
#define USER_DATA_SELECTOR 0x18
#define USER_CODE_SELECTOR 0x20
#define TSS_SELECTOR 0x28

/* The IDT's interrupt-stack indices for the vectors that get a stack of their own (gdt.c). */
#define IST_DOUBLE_FAULT 1
#define IST_NMI 2
#define IST_MACHINE_CHECK 3

/* The 256 interrupt and exception stubs are VECTOR_STUB_SIZE bytes apart (vectors.S). */
#define VECTOR_STUB_SIZE 16
#define VECTOR_COUNT 256

#ifndef __ASSEMBLER__

#include <stdint.h>
#include <stdnoreturn.h>

/*
 * The start-up steps, which port_startup runs in this order before it calls kmain. Each does only
 * work on the CPU and through I/O ports.
 */
noreturn void port_startup(void);
void gdt_load(void);
void idt_load(void);
void cpu_setup(void);
void pic_mask(void);
void tsc_calibrate(void);

/*
 * Where every interrupt and exception stub ends up (vectors.S), and where the CPU goes on a
 * SYSCALL. Neither has anything to hand the event to yet, so both end the run with the panic
 * outcome instead of letting a triple fault reset the machine.
 */
noreturn void port_trap(void);
void port_syscall_entry(void);

/* The operand of LGDT and LIDT. */
struct descriptor_pointer {
    uint16_t limit;
    uint64_t base;
} __attribute__((packed));

/* The first of the interrupt and exception stubs. */
extern const char port_vectors[];

static inline uint8_t inb(uint16_t port) {
    uint8_t value;
    __asm__ volatile("inb %1, %0" : "=a"(value) : "Nd"(port));
    return value;
}

static inline void outb(uint16_t port, uint8_t value) {
    __asm__ volatile("outb %0, %1" : : "a"(value), "Nd"(port));
}

static inline uint64_t rdmsr(uint32_t msr) {
    uint32_t low;
    uint32_t high;
    __asm__ volatile("rdmsr" : "=a"(low), "=d"(high) : "c"(msr));
    return ((uint64_t)high << 32U) | low;
}

static inline void wrmsr(uint32_t msr, uint64_t value) {
    __asm__ volatile("wrmsr" : : "c"(msr), "a"((uint32_t)value), "d"((uint32_t)(value >> 32U)));
}

static inline uint64_t rdtsc(void) {
    uint32_t low;
    uint32_t high;
    __asm__ volatile("rdtsc" : "=a"(low), "=d"(high));
    return ((uint64_t)high << 32U) | low;
}

struct cpuid {
    uint32_t eax, ebx, ecx, edx;
};

static inline struct cpuid cpuid(uint32_t leaf, uint32_t subleaf) {
    struct cpuid r;
    __asm__ volatile("cpuid"
                     : "=a"(r.eax), "=b"(r.ebx), "=c"(r.ecx), "=d"(r.edx)
                     : "a"(leaf), "c"(subleaf));
    return r;
}

#endif

#endif
