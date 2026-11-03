import argparse, glob, os, shutil, sys, tarfile, urllib.request

import common

SDL2_VERSION = "2.32.10"

BASE_PACKAGES = ["binutils", "musl-dev", "linux-headers", "gcc", "libc++-dev", "libc++-static",
                 "llvm-libunwind-dev", "llvm-libunwind-static"]
BUILD_PACKAGES = ["cmake", "ninja", "g++", "make", "libx11-dev", "libxext-dev", "libxrandr-dev",
                  "libxcursor-dev", "libxi-dev", "libxfixes-dev", "libxrender-dev", "libxscrnsaver-dev",
                  "alsa-lib-dev", "mesa-dev", "eudev-dev"]
COMPILER_HEADERS = ["float.h", "iso646.h", "stdalign.h", "stdarg.h", "stdbool.h", "stddef.h",
                    "stdnoreturn.h", "tgmath.h"]
SKIP_HEADERS = ["c++", "python3.12", "mach-o"]
RUNTIME_HEADERS = ["__libunwind_config.h", "libunwind.h", "libunwind.modulemap", "unwind.h",
                   "unwind_arm_ehabi.h", "unwind_itanium.h"]
CRT_FILES = ["crt1.o", "crti.o", "crtn.o", "Scrt1.o", "rcrt1.o"]
LIB_FILES = ["libc.a", "libc.so", "libm.a", "libpthread.a", "libdl.a", "librt.a", "libutil.a",
             "libresolv.a", "libcrypt.a", "libxnet.a"]


def copy_files(patterns, dst_dir):
    count = 0
    for pattern in patterns:
        for src in sorted(glob.glob(pattern)):
            if os.path.isfile(src):
                os.makedirs(dst_dir, exist_ok=True)
                shutil.copy2(src, dst_dir)
                count += 1
    return count


def collect_base(out):
    std_inc = os.path.join(out, "standard", "include")
    rt_inc = os.path.join(out, "runtime", "include")
    for name in sorted(os.listdir("/usr/include")):
        src = os.path.join("/usr/include", name)
        if name in SKIP_HEADERS or name in COMPILER_HEADERS:
            continue
        dst = rt_inc if name in RUNTIME_HEADERS else std_inc
        os.makedirs(dst, exist_ok=True)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(dst, name), symlinks=False)
        else:
            shutil.copy2(src, dst)
    if not os.path.isdir("/usr/include/c++/v1"):
        sys.exit("libc++ headers not found")
    shutil.copytree("/usr/include/c++/v1", os.path.join(rt_inc, "c++", "v1"))

    std_lib = os.path.join(out, "standard", "lib")
    rt_lib = os.path.join(out, "runtime", "lib")
    if copy_files(["/usr/lib/" + n for n in CRT_FILES + LIB_FILES], std_lib) == 0:
        sys.exit("musl libraries not found")
    copy_files(["/lib/ld-musl-*.so.1"], std_lib)
    copy_files(["/usr/lib/libc++.a", "/usr/lib/libc++abi.a", "/usr/lib/libunwind.a"], rt_lib)
    copy_files(["/usr/lib/gcc/*/*/libgcc.a", "/usr/lib/gcc/*/*/libgcc_eh.a",
                "/usr/lib/gcc/*/*/crtbegin*.o", "/usr/lib/gcc/*/*/crtend*.o"], rt_lib)
    if not glob.glob(os.path.join(rt_lib, "libc++.a")):
        sys.exit("libc++.a not found")
    if not glob.glob(os.path.join(rt_lib, "libgcc.a")):
        sys.exit("libgcc.a not found")


def collect_graphics(out, work):
    prefix = os.path.join(work, "prefix")
    archive = os.path.join(work, "SDL2.tar.gz")
    url = "https://github.com/libsdl-org/SDL/releases/download/release-%s/SDL2-%s.tar.gz" % (SDL2_VERSION, SDL2_VERSION)
    print("download " + url, flush=True)
    urllib.request.urlretrieve(url, archive)
    with tarfile.open(archive) as tf:
        tf.extractall(work)
    build = os.path.join(work, "sdl2-build")
    common.run(["cmake", "-S", os.path.join(work, "SDL2-" + SDL2_VERSION), "-B", build, "-G", "Ninja",
                "-DCMAKE_BUILD_TYPE=Release", "-DCMAKE_INSTALL_PREFIX=" + prefix,
                "-DSDL_SHARED=OFF", "-DSDL_STATIC=ON", "-DSDL_TEST=OFF", "-DSDL_TESTS=OFF"])
    common.run(["cmake", "--build", build, "--parallel"])
    common.run(["cmake", "--install", build])
    gfx = os.path.join(out, "graphics")
    shutil.copytree(os.path.join(prefix, "include"), os.path.join(gfx, "include"))
    if copy_files([os.path.join(prefix, "lib", "libSDL2.a"), os.path.join(prefix, "lib", "libSDL2main.a")],
                  os.path.join(gfx, "lib")) != 2:
        sys.exit("SDL2 static libraries not installed")
    for path in glob.glob(os.path.join(gfx, "include", "SDL2", "SDL_test*.h")):
        os.remove(path)


def strip_debug(out):
    count = 0
    for pattern in ("standard/lib/*.a", "standard/lib/*.o", "runtime/lib/*.a", "runtime/lib/*.o", "graphics/lib/*.a"):
        for path in sorted(glob.glob(os.path.join(out, pattern))):
            common.run(["strip", "--strip-debug", path])
            count += 1
    print("stripped debug info from %d files" % count)


def build(arch, out, work):
    for d in (out, work):
        if os.path.exists(d):
            shutil.rmtree(d)
    os.makedirs(work)
    common.run(["apk", "add", "--no-cache"] + BASE_PACKAGES)
    collect_base(out)
    common.run(["apk", "add", "--no-cache"] + BUILD_PACKAGES)
    collect_graphics(out, work)
    strip_debug(out)
    with open(os.path.join(out, "SOURCE.txt"), "w") as f:
        f.write("alpine musl, arch " + arch + "\nSDL2 " + SDL2_VERSION + " static\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--arg", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--work", default="/tmp/sdk-work")
    a = p.parse_args()
    build(a.arg, a.out, a.work)


if __name__ == "__main__":
    main()
