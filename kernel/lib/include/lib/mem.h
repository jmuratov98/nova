#ifndef LIB_MEM_H
#define LIB_MEM_H

#include <stddef.h>

/*
 * The four functions the compiler emits calls to, under their standard names. They are lib's only
 * unprefixed exports. NOVA_EXPORT comes from the build's prelude (mk/prelude.h).
 */

NOVA_EXPORT void *memcpy(void *restrict dst, const void *restrict src, size_t n);
NOVA_EXPORT void *memmove(void *dst, const void *src, size_t n);
NOVA_EXPORT void *memset(void *dst, int value, size_t n);
NOVA_EXPORT int memcmp(const void *a, const void *b, size_t n);

#endif
