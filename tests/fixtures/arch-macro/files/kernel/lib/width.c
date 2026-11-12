void lib_width(int *out);

void lib_width(int *out) {
#ifdef __x86_64__
    *out = 8;
#else
    *out = 4;
#endif
}
