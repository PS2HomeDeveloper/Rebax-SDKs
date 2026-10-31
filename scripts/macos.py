import argparse, glob, os, shutil, subprocess, sys, tarfile, urllib.request

import common

SDL2_VERSION = "2.32.10"
DEPLOYMENT = "11.0"

SKIP_PREFIXES = ("ruby", "python", "tcl", "tk", "perl", "php", "apache")
SKIP_INCLUDE = ["c++", "module.modulemap"]
RUNTIME_LIBS = ["libc++.tbd", "libc++abi.tbd", "libunwind.tbd"]

STANDARD_FRAMEWORKS = ["CoreFoundation", "Foundation", "CoreServices", "Security", "IOKit",
                       "ApplicationServices", "CoreGraphics", "ImageIO"]
GRAPHICS_FRAMEWORKS = ["Cocoa", "AppKit", "CoreAudio", "AudioToolbox", "CoreVideo", "OpenGL",
                       "Metal", "QuartzCore", "ForceFeedback", "Carbon", "CoreHaptics",
                       "GameController", "CoreMedia", "CoreText", "CoreImage", "CoreData",
                       "AudioUnit", "CoreAudioTypes", "CoreMIDI", "UniformTypeIdentifiers"]


def capture(cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()


def flatten_framework(src, dst):
    version = os.path.join(src, "Versions", "A")
    base = version if os.path.isdir(version) else src
    name = os.path.basename(src)[:-len(".framework")]
    os.makedirs(dst, exist_ok=True)
    headers = os.path.join(base, "Headers")
    if os.path.isdir(headers):
        shutil.copytree(headers, os.path.join(dst, "Headers"), symlinks=False)
    for tbd in glob.glob(os.path.join(base, "*.tbd")) + glob.glob(os.path.join(src, "*.tbd")):
        shutil.copy2(tbd, os.path.join(dst, os.path.basename(tbd)))
        if os.path.basename(tbd) == name + ".tbd" and not os.path.exists(os.path.join(dst, name)):
            shutil.copy2(tbd, os.path.join(dst, name))
    sub = os.path.join(base, "Frameworks")
    if os.path.isdir(sub):
        for child in sorted(os.listdir(sub)):
            if child.endswith(".framework"):
                flatten_framework(os.path.join(sub, child), os.path.join(dst, "Frameworks", child))


def copy_frameworks(sdk, names, dst):
    root = os.path.join(sdk, "System", "Library", "Frameworks")
    for name in names:
        src = os.path.join(root, name + ".framework")
        if not os.path.isdir(src):
            print("skip (not in this SDK): " + name)
            continue
        flatten_framework(src, os.path.join(dst, name + ".framework"))


def collect_base(sdk, out):
    inc = os.path.join(sdk, "usr", "include")
    std_inc = os.path.join(out, "standard", "include")
    os.makedirs(std_inc)
    for name in sorted(os.listdir(inc)):
        if name in SKIP_INCLUDE or name.startswith(SKIP_PREFIXES):
            continue
        src = os.path.join(inc, name)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(std_inc, name), symlinks=False)
        else:
            shutil.copy2(src, std_inc)
    cxx = os.path.join(inc, "c++")
    if not os.path.isdir(cxx):
        sys.exit("libc++ headers not found in the SDK")
    shutil.copytree(cxx, os.path.join(out, "runtime", "include", "c++"), symlinks=False)

    std_lib = os.path.join(out, "standard", "lib")
    rt_lib = os.path.join(out, "runtime", "lib")
    os.makedirs(std_lib)
    os.makedirs(rt_lib)
    ulib = os.path.join(sdk, "usr", "lib")
    for path in sorted(glob.glob(os.path.join(ulib, "*.tbd"))):
        name = os.path.basename(path)
        shutil.copy2(path, os.path.join(rt_lib if name in RUNTIME_LIBS else std_lib, name))
    system = os.path.join(ulib, "system")
    if os.path.isdir(system):
        shutil.copytree(system, os.path.join(std_lib, "system"), symlinks=False)
    if not os.path.exists(os.path.join(std_lib, "libSystem.tbd")):
        sys.exit("libSystem.tbd not found")

    resource = capture(["clang", "-print-resource-dir"])
    rt = os.path.join(resource, "lib", "darwin", "libclang_rt.osx.a")
    if not os.path.isfile(rt):
        sys.exit("libclang_rt.osx.a not found: " + rt)
    shutil.copy2(rt, rt_lib)

    copy_frameworks(sdk, STANDARD_FRAMEWORKS, os.path.join(out, "standard", "Frameworks"))


def collect_graphics(sdk, arch, out, work):
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
                "-DCMAKE_OSX_ARCHITECTURES=" + arch, "-DCMAKE_OSX_DEPLOYMENT_TARGET=" + DEPLOYMENT,
                "-DCMAKE_OSX_SYSROOT=" + sdk,
                "-DSDL_SHARED=OFF", "-DSDL_STATIC=ON", "-DSDL_TEST=OFF", "-DSDL_TESTS=OFF"])
    common.run(["cmake", "--build", build, "--parallel"])
    common.run(["cmake", "--install", build])
    gfx = os.path.join(out, "graphics")
    shutil.copytree(os.path.join(prefix, "include"), os.path.join(gfx, "include"))
    os.makedirs(os.path.join(gfx, "lib"))
    for name in ("libSDL2.a", "libSDL2main.a"):
        src = os.path.join(prefix, "lib", name)
        if not os.path.isfile(src):
            sys.exit("not installed: " + name)
        shutil.copy2(src, os.path.join(gfx, "lib"))
    for path in glob.glob(os.path.join(gfx, "include", "SDL2", "SDL_test*.h")):
        os.remove(path)
    copy_frameworks(sdk, GRAPHICS_FRAMEWORKS, os.path.join(gfx, "Frameworks"))


def build(arch, out, work):
    for d in (out, work):
        if os.path.exists(d):
            shutil.rmtree(d)
    os.makedirs(work)
    sdk = os.path.realpath(capture(["xcrun", "--sdk", "macosx", "--show-sdk-path"]))
    print("sdk: " + sdk, flush=True)
    collect_base(sdk, out)
    collect_graphics(sdk, arch, out, work)
    with open(os.path.join(out, "SOURCE.txt"), "w") as f:
        f.write("macOS SDK: " + os.path.basename(sdk) + "\narch " + arch + "\nSDL2 " + SDL2_VERSION +
                " static\ndeployment target " + DEPLOYMENT + "\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--arg", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--work", default="sdk-work")
    a = p.parse_args()
    build(a.arg, a.out, os.path.abspath(a.work))


if __name__ == "__main__":
    main()
