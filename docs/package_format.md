# Package format

## File name

```
rebax-sdk-<id>.tar.xz
```

`<id>` is the target id, for example `linux-x86_64`. The archive is compressed with xz and has exactly one top folder, named `<id>`. Extracting it inside the `sdks` folder of Rebax produces `sdks/<id>`.

## Layout

Every package uses the same three folders.

| Folder | Content |
| --- | --- |
| `standard` | The C library of the target, with its headers and startup files. This is the sysroot used by the compiler. |
| `runtime` | The compiler runtime of the target, such as `libclang_rt.builtins` and, on Android, `libc++_shared.so`. |
| `graphics` | The SDL2 library of the target: headers in `include/SDL2` and libraries in `lib`. |

The PlayStation 2 package follows the same scheme: `standard` holds the PS2 SDK and `graphics` holds gsKit.

### Platform details

- **Linux**: the C library is musl and SDL2 is a static library, so a Rebax executable for Linux is a single file.
- **Windows**: the package contains the import library `libSDL2.dll.a` and `bin/SDL2.dll`. When the package also contains a static `libSDL2.a`, Rebax links SDL2 statically and the executable is a single file.
- **Android**: `graphics/lib` contains `libSDL2.so`, `libiconv.so` and `libcharset.so`. `graphics/java` contains the SDL2 Java sources, and `graphics/dex/classes.dex` is the compiled form of them. Rebax puts this file into the APK, so no Java tools are needed to build an APK.

## Checksums

`manifest.json` in the release lists each package with its file name, size and SHA-256 checksum. A mismatch is reported as a warning by Rebax.

## Version

Rebax always downloads from the latest release. A new release replaces the packages as a whole.
