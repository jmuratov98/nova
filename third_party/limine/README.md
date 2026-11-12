# limine.h

The Limine boot protocol's C header, vendored so that compiling the kernel never needs the
network. Only `boot` may include it, which `kernel/subsystems.toml` declares.

| | |
|---|---|
| Source | [`limine-protocol`](https://github.com/Limine-Bootloader/limine-protocol), `include/limine.h` |
| Commit | `6e85ddd6f928b5b512015c4d47d1cfce2fd28079`, the one Limine v12.9.6's `bootstrap` pins |
| sha256 | `0aadf2633c85d8cb145344c968add158aeb1deb68af567d55ba8431c492b6d4c` |
| License | 0BSD, in the header's own comment |

The file is unmodified. It is byte for byte the copy bundled in the `limine-12.9.6.tar.gz` release
tarball, whose sha256 is `5022d02c0709ccf3cd6702e89206e2e8c953d253d80fc05b276a526c23719332`.

To update it, take the commit that the new Limine release's `bootstrap` pins, together with the
bump of `LIMINE_VERSION` and `LIMINE_SHA256` in `mk/image.mk`.
