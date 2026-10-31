import argparse, glob, os, shutil, sys, tarfile, urllib.request

import common

MINGW_VERSION = "20250709"
SDL2_VERSION = "2.32.10"

ARCHS = {
    "x86_64": {"triple": "x86_64-w64-mingw32", "cpu": "x86_64", "rt": "x86_64"},
    "x86": {"triple": "i686-w64-mingw32", "cpu": "i686", "rt": "i386"},
    "arm": {"triple": "armv7-w64-mingw32", "cpu": "arm", "rt": "arm"},
    "arm64": {"triple": "aarch64-w64-mingw32", "cpu": "aarch64", "rt": "aarch64"},
}

RUNTIME_HEADERS = ["c++", "__libunwind_config.h", "libunwind.h", "libunwind.modulemap",
                   "unwind.h", "unwind_arm_ehabi.h", "unwind_itanium.h"]
RUNTIME_LIB_PREFIXES = ("libc++", "libunwind")
LIB_SKIP = ("libomp", "libclang_rt", "libwinpthread.la")
LIB_SKIP_SUFFIX = (".modules.json", ".la")
RUNTIME_DLLS = ["libc++.dll", "libunwind.dll"]
STANDARD_DLLS = ["libwinpthread-1.dll"]


def fetch(url, dest):
    print("download " + url, flush=True)
    urllib.request.urlretrieve(url, dest)


def get_mingw(work):
    name = "llvm-mingw-%s-ucrt-ubuntu-22.04-x86_64" % MINGW_VERSION
    archive = os.path.join(work, name + ".tar.xz")
    fetch("https://github.com/mstorsjo/llvm-mingw/releases/download/%s/%s.tar.xz" % (MINGW_VERSION, name), archive)
    with tarfile.open(archive) as tf:
        tf.extractall(work)
    os.remove(archive)
    root = os.path.join(work, name)
    if not os.path.isdir(os.path.join(root, "generic-w64-mingw32")):
        sys.exit("unexpected llvm-mingw layout: " + root)
    return root


def copy_one(src, dst_dir):
    os.makedirs(dst_dir, exist_ok=True)
    shutil.copy2(src, dst_dir, follow_symlinks=False)


def build_standard_and_runtime(arch, root, out):
    info = ARCHS[arch]
    inc = os.path.join(root, "generic-w64-mingw32", "include")
    std_inc = os.path.join(out, "standard", "include")
    rt_inc = os.path.join(out, "runtime", "include")
    os.makedirs(std_inc)
    os.makedirs(rt_inc)
    for name in sorted(os.listdir(inc)):
        src = os.path.join(inc, name)
        if name in RUNTIME_HEADERS:
            dst = rt_inc
        elif name == "ddk" or name.endswith(".idl"):
            continue
        else:
            dst = std_inc
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(dst, name), symlinks=True)
        else:
            shutil.copy2(src, dst)

    tdir = os.path.join(root, info["triple"])
    for name in sorted(os.listdir(os.path.join(tdir, "lib"))):
        src = os.path.join(tdir, "lib", name)
        if not os.path.isfile(src):
            continue
        if name.startswith(RUNTIME_LIB_PREFIXES) and not name.endswith(LIB_SKIP_SUFFIX):
            copy_one(src, os.path.join(out, "runtime", "lib"))
        elif name.startswith(LIB_SKIP) or name.endswith(LIB_SKIP_SUFFIX):
            continue
        else:
            copy_one(src, os.path.join(out, "standard", "lib"))
    for name in RUNTIME_DLLS:
        copy_one(os.path.join(tdir, "bin", name), os.path.join(out, "runtime", "bin"))
    for name in STANDARD_DLLS:
        copy_one(os.path.join(tdir, "bin", name), os.path.join(out, "standard", "bin"))

    builtins = glob.glob(os.path.join(root, "lib", "clang", "*", "lib", "windows", "libclang_rt.builtins-%s.a" % info["rt"]))
    if not builtins:
        sys.exit("compiler-rt builtins not found for " + arch)
    copy_one(builtins[0], os.path.join(out, "runtime", "lib"))


def build_graphics(arch, root, out, work):
    info = ARCHS[arch]
    prefix = os.path.join(work, "prefix")
    sdl_tar = os.path.join(work, "SDL2.tar.gz")
    fetch("https://github.com/libsdl-org/SDL/releases/download/release-%s/SDL2-%s.tar.gz" % (SDL2_VERSION, SDL2_VERSION), sdl_tar)
    with tarfile.open(sdl_tar) as tf:
        tf.extractall(work)
    bindir = os.path.join(root, "bin")
    triple = info["triple"]
    build = os.path.join(work, "sdl2-build")
    common.run(["cmake", "-S", os.path.join(work, "SDL2-" + SDL2_VERSION), "-B", build, "-G", "Ninja",
                "-DCMAKE_SYSTEM_NAME=Windows", "-DCMAKE_SYSTEM_PROCESSOR=" + info["cpu"],
                "-DCMAKE_C_COMPILER=" + os.path.join(bindir, triple + "-clang"),
                "-DCMAKE_CXX_COMPILER=" + os.path.join(bindir, triple + "-clang++"),
                "-DCMAKE_RC_COMPILER=" + os.path.join(bindir, triple + "-windres"),
                "-DCMAKE_BUILD_TYPE=Release", "-DCMAKE_INSTALL_PREFIX=" + prefix,
                "-DSDL_SHARED=ON", "-DSDL_STATIC=OFF", "-DSDL_TEST=OFF", "-DSDL_TESTS=OFF"])
    common.run(["cmake", "--build", build, "--parallel"])
    common.run(["cmake", "--install", build])

    gfx = os.path.join(out, "graphics")
    shutil.copytree(os.path.join(prefix, "include"), os.path.join(gfx, "include"))
    for pattern, dst in [("lib/libSDL2.dll.a", "lib"), ("lib/libSDL2main.a", "lib"), ("bin/SDL2.dll", "bin")]:
        found = glob.glob(os.path.join(prefix, pattern))
        if not found:
            sys.exit("not installed: " + pattern)
        copy_one(found[0], os.path.join(gfx, dst))


PRUNE = [
    "runtime/lib/libc++experimental.a",
    "graphics/include/SDL2/SDL_test*.h",
]


def prune(out):
    for pattern in PRUNE:
        for path in glob.glob(os.path.join(out, pattern)):
            os.remove(path)
            print("removed " + os.path.relpath(path, out))


def build(arch, out):
    if arch not in ARCHS:
        sys.exit("unknown arch " + arch)
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    work = os.path.abspath("windows-work-" + arch)
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    root = get_mingw(work)
    build_standard_and_runtime(arch, root, out)
    build_graphics(arch, root, out, work)
    prune(out)
    with open(os.path.join(out, "SOURCE.txt"), "w") as f:
        f.write("llvm-mingw %s (ucrt)\nsdl2: %s\n" % (MINGW_VERSION, SDL2_VERSION))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--arg", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    build(a.arg, a.out)


if __name__ == "__main__":
    main()
