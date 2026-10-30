import argparse, glob, os, shutil, subprocess, sys, tarfile, urllib.request

import common

API = "21"
SDL2_VERSION = "2.32.10"
LIBICONV_VERSION = "1.17"

ABIS = {
    "arm64-v8a": {"clang": "aarch64-linux-android", "lib": "aarch64-linux-android", "rt": "aarch64", "rtdir": "aarch64"},
    "armeabi-v7a": {"clang": "armv7a-linux-androideabi", "lib": "arm-linux-androideabi", "rt": "arm", "rtdir": "arm"},
    "x86": {"clang": "i686-linux-android", "lib": "i686-linux-android", "rt": "i686", "rtdir": "i386"},
    "x86_64": {"clang": "x86_64-linux-android", "lib": "x86_64-linux-android", "rt": "x86_64", "rtdir": "x86_64"},
}
ALL_LIB_TRIPLES = ["aarch64-linux-android", "arm-linux-androideabi", "i686-linux-android", "x86_64-linux-android", "riscv64-linux-android"]


def ndk_paths():
    root = os.environ.get("ANDROID_NDK_HOME") or os.environ.get("ANDROID_NDK_LATEST_HOME")
    if not root:
        sys.exit("ANDROID_NDK_HOME is not set")
    llvm = os.path.join(root, "toolchains", "llvm", "prebuilt", "linux-x86_64")
    return root, llvm, os.path.join(llvm, "sysroot")


def build_standard(abi, sysroot, out):
    info = ABIS[abi]
    other = set(ALL_LIB_TRIPLES) - {info["lib"]}

    def skip_include(directory, names):
        if os.path.basename(directory) == "include":
            return [n for n in names if n == "c++" or n in other]
        return []

    src_inc = os.path.join(sysroot, "usr", "include")
    shutil.copytree(src_inc, os.path.join(out, "standard", "usr", "include"), symlinks=True, ignore=skip_include)
    libdir = os.path.join(sysroot, "usr", "lib", info["lib"])
    dst = os.path.join(out, "standard", "usr", "lib", info["lib"])
    os.makedirs(dst)
    for name in sorted(os.listdir(libdir)):
        src = os.path.join(libdir, name)
        if os.path.isfile(src) and not name.startswith("libc++"):
            shutil.copy2(src, os.path.join(dst, name))
        elif os.path.isdir(src) and name == API:
            shutil.copytree(src, os.path.join(dst, name), symlinks=True)
    if not os.path.isdir(os.path.join(dst, API)):
        sys.exit("API folder %s not found in %s" % (API, libdir))


def build_runtime(abi, llvm, sysroot, out):
    info = ABIS[abi]
    rt = os.path.join(out, "runtime")
    cxx = os.path.join(sysroot, "usr", "include", "c++")
    if not os.path.isdir(cxx):
        sys.exit("libc++ headers not found: " + cxx)
    shutil.copytree(cxx, os.path.join(rt, "include", "c++"), symlinks=True)
    libdir = os.path.join(sysroot, "usr", "lib", info["lib"])
    dst = os.path.join(rt, "lib", info["lib"])
    os.makedirs(dst)
    found = 0
    for src in sorted(glob.glob(os.path.join(libdir, "libc++*"))):
        shutil.copy2(src, dst)
        found += 1
    for base in glob.glob(os.path.join(llvm, "lib", "clang", "*", "lib", "linux")):
        for src in glob.glob(os.path.join(base, "libclang_rt.builtins-%s-android*" % info["rt"])):
            shutil.copy2(src, dst)
            found += 1
        sub = os.path.join(base, info["rtdir"])
        if os.path.isdir(sub):
            for name in sorted(os.listdir(sub)):
                shutil.copy2(os.path.join(sub, name), dst)
                found += 1
    if found == 0:
        sys.exit("no runtime libraries found")


def fetch(url, dest):
    print("download " + url, flush=True)
    urllib.request.urlretrieve(url, dest)


def build_graphics(abi, ndk, llvm, out, work):
    info = ABIS[abi]
    prefix = os.path.join(work, "prefix")
    os.makedirs(prefix, exist_ok=True)
    sdl_tar = os.path.join(work, "SDL2.tar.gz")
    fetch("https://github.com/libsdl-org/SDL/releases/download/release-%s/SDL2-%s.tar.gz" % (SDL2_VERSION, SDL2_VERSION), sdl_tar)
    with tarfile.open(sdl_tar) as tf:
        tf.extractall(work)
    common.run(["cmake", "-S", os.path.join(work, "SDL2-" + SDL2_VERSION), "-B", os.path.join(work, "sdl2-build"),
                "-DCMAKE_TOOLCHAIN_FILE=" + os.path.join(ndk, "build", "cmake", "android.toolchain.cmake"),
                "-DANDROID_ABI=" + abi, "-DANDROID_PLATFORM=android-" + API,
                "-DCMAKE_BUILD_TYPE=Release", "-DCMAKE_INSTALL_PREFIX=" + prefix,
                "-DSDL_SHARED=ON", "-DSDL_STATIC=OFF"])
    common.run(["cmake", "--build", os.path.join(work, "sdl2-build"), "--parallel"])
    common.run(["cmake", "--install", os.path.join(work, "sdl2-build")])

    iconv_tar = os.path.join(work, "libiconv.tar.gz")
    fetch("https://ftp.gnu.org/gnu/libiconv/libiconv-%s.tar.gz" % LIBICONV_VERSION, iconv_tar)
    with tarfile.open(iconv_tar) as tf:
        tf.extractall(work)
    cc = os.path.join(llvm, "bin", info["clang"] + API + "-clang")
    if not os.path.exists(cc):
        sys.exit("compiler not found: " + cc)
    src = os.path.join(work, "libiconv-" + LIBICONV_VERSION)
    build_triple = subprocess.run(["gcc", "-dumpmachine"], capture_output=True, text=True, check=True).stdout.strip()
    common.run(["./configure", "--build=" + build_triple, "--host=" + info["clang"], "--prefix=" + prefix,
                "--enable-shared", "--disable-static", "--disable-nls",
                "CC=" + cc, "CPPFLAGS=-DO_BINARY=0", "CFLAGS=-fPIC -DO_BINARY=0"], cwd=src)
    common.run(["make", "-j4"], cwd=src)
    common.run(["make", "install"], cwd=src)

    gfx = os.path.join(out, "graphics")
    shutil.copytree(os.path.join(prefix, "include"), os.path.join(gfx, "include"), symlinks=True)
    os.makedirs(os.path.join(gfx, "lib"))
    count = 0
    for name in sorted(os.listdir(os.path.join(prefix, "lib"))):
        p = os.path.join(prefix, "lib", name)
        if (name.endswith(".so") or ".so." in name) and not os.path.isdir(p):
            if os.path.islink(p):
                os.symlink(os.readlink(p), os.path.join(gfx, "lib", name))
            else:
                shutil.copy2(p, os.path.join(gfx, "lib", name))
            count += 1
    if count == 0:
        sys.exit("no shared libraries were installed for graphics")


def build(abi, out):
    if abi not in ABIS:
        sys.exit("unknown abi " + abi)
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    ndk, llvm, sysroot = ndk_paths()
    work = os.path.abspath("android-work-" + abi)
    os.makedirs(work, exist_ok=True)
    build_standard(abi, sysroot, out)
    build_runtime(abi, llvm, sysroot, out)
    build_graphics(abi, ndk, llvm, out, work)
    with open(os.path.join(out, "SOURCE.txt"), "w") as f:
        f.write("ndk: %s\napi: %s\nsdl2: %s\nlibiconv: %s\n" % (os.path.basename(ndk), API, SDL2_VERSION, LIBICONV_VERSION))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--arg", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    build(a.arg, a.out)


if __name__ == "__main__":
    main()
