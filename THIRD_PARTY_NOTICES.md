# Third party notices

The SDK packages are assembled from the projects below. Each project keeps its own license, and the license terms of a project apply to the files that come from it.

| Project | Used for | License |
| --- | --- | --- |
| SDL2 | Graphics, window and input library in every package | zlib |
| musl libc | C library of the Linux packages | MIT |
| LLVM compiler runtime and libc++ | Compiler runtime of the packages, and `libc++_shared.so` on Android | Apache 2.0 with LLVM exceptions |
| Android NDK | Android sysroot and libraries | Apache 2.0 and the licenses of its components |
| mingw-w64 | Windows C runtime and headers | See the license files of mingw-w64 |
| libiconv and libcharset | Required by SDL2 on Android | LGPL 2.1 or later |
| ps2sdk and gsKit | PlayStation 2 SDK and graphics library | See the license files of the ps2dev projects |

The exact versions are written in the `SOURCE.txt` file of each package when the build script provides one.
