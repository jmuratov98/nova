#include <stdint.h>

#include <limine.h>

/*
 * The requests that Limine reads from the kernel image before it starts the kernel. They are never
 * referenced, so they are marked used, and volatile, because Limine writes its answers into them.
 *
 * Limine honours only the requests between the two markers, and looks for them only in the image's
 * initialised data, not in the zero-filled tail of its last segment. The linker script keeps the
 * three sections in this order at the start of .data.
 */

__attribute__((used, section(".limine_requests_start"))) static volatile uint64_t requests_start[] =
    LIMINE_REQUESTS_START_MARKER;

/*
 * Base revision 6, the newest, which fixes the machine state at entry and what the higher-half
 * direct map covers. Limine sets the third word to 0 when it honours it, and the second to the
 * revision it loaded the kernel with.
 */
__attribute__((used, section(".limine_requests"))) static volatile uint64_t base_revision[] =
    LIMINE_BASE_REVISION(6);

__attribute__((used, section(".limine_requests_end"))) static volatile uint64_t requests_end[] =
    LIMINE_REQUESTS_END_MARKER;
