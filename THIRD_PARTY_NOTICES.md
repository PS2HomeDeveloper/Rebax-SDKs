# Third-Party Notices

The SDK packages are assembled from the projects below. Each project keeps its own license, and the terms of that license apply to the files that come from it. The packages themselves are not licensed under this repository's MIT License.

## Packages for Linux, Windows, macOS, iOS and Android

| Project | Used for | License | Source |
| --- | --- | --- | --- |
| SDL2 | Window, graphics and input library in every package | zlib License | https://github.com/libsdl-org/SDL |
| musl libc | C library of the Linux packages | MIT License | https://musl.libc.org |
| LLVM compiler-rt and libc++ | Compiler runtime of the packages, and `libc++_shared.so` on Android | Apache License 2.0 with LLVM Exceptions | https://github.com/llvm/llvm-project |
| mingw-w64 | C runtime and headers of the Windows packages | Zope Public License 2.1, with parts in the public domain or under permissive licenses | https://www.mingw-w64.org |
| Android NDK | Sysroot and libraries of the Android packages | Apache License 2.0, and the licenses of its components | https://developer.android.com/ndk |
| Apple SDK stubs | Link stubs of the macOS and iOS packages, taken from the Xcode SDK on the build machine | Apple SDK license | https://developer.apple.com/xcode/ |

### GNU libiconv and libcharset

The Android packages contain `libiconv.so` and `libcharset.so`, built from GNU libiconv 1.17 because SDL2 requires them on Android.

- License: GNU Lesser General Public License 2.1 or later.
- Source code: https://ftp.gnu.org/gnu/libiconv/libiconv-1.17.tar.gz
- The libraries are shared libraries. They are not linked statically into Rebax programs, so you can replace them with a modified version of your own.

If you distribute a program that includes these libraries, you must comply with the terms of the LGPL.

## PlayStation 2 package

| Project | Used for | License | Source |
| --- | --- | --- | --- |
| ps2sdk | PlayStation 2 libraries and headers | Academic Free License 2.0 | https://github.com/ps2dev/ps2sdk |
| gsKit | PlayStation 2 graphics library | Academic Free License 2.0 | https://github.com/ps2dev/gsKit |
| ps2link | Network loader `ps2link.elf` | Academic Free License 2.0 | https://github.com/ps2dev/ps2link |
| GCC runtime libraries (libgcc, libstdc++) | Compiler runtime | GNU GPL 3.0 or later with the GCC Runtime Library Exception | https://gcc.gnu.org |

The GCC Runtime Library Exception allows programs built with these libraries to be distributed under terms of your choice.

## PlayStation 1 package

| Project | Used for | License | Source |
| --- | --- | --- | --- |
| PSn00bSDK | PlayStation 1 libraries and headers | Mozilla Public License 2.0, with some parts under other permissive licenses listed in its repository | https://github.com/Lameguy64/PSn00bSDK |

## Versions

The versions that were used are written in the `SOURCE.txt` file of each package when the build script provides one.

## Reporting a mistake

If a project is missing or a license is described incorrectly, please open an issue in the [Rebax repository](https://github.com/PS2HomeDeveloper/Rebax/issues).
