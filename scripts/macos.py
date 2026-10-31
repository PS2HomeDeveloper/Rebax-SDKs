import argparse, glob, os, shutil, subprocess, sys, tarfile, urllib.request

import common

SDL2_VERSION = "2.32.10"
DEPLOYMENT = "11.0"

IGNORE = shutil.ignore_patterns("*.modulemap", "*.apinotes", "*.swiftcrossimport")
SKIP_PREFIXES = ("ruby", "python", "tcl", "tk", "perl", "php", "apache")
SKIP_INCLUDE = ["c++", "_modules", "AppleArchive", "EndpointSecurity", "Spatial", "apr-1", "cups", "curl",
                "editline", "ffi", "gssapi", "hvf", "krb5", "ldap", "libexslt", "libxml", "libxml2",
                "libxslt", "net-snmp", "pcap", "readline", "sasl", "tidy", "xar"]
SKIP_SUFFIXES = (".modulemap", ".apinotes", ".swiftcrossimport")
RUNTIME_LIBS = ["libc++.tbd", "libc++.1.tbd", "libc++abi.tbd", "libunwind.tbd"]
STANDARD_LIBS = ["libSystem.tbd", "libSystem.B.tbd", "libc.tbd", "libm.tbd", "libdl.tbd", "libpthread.tbd",
                 "libutil.tbd", "libresolv.tbd", "libresolv.9.tbd", "libinfo.tbd", "libobjc.tbd",
                 "libobjc.A.tbd", "libz.tbd", "libz.1.tbd", "libiconv.tbd", "libiconv.2.tbd",
                 "libcharset.tbd", "libcharset.1.tbd", "libcompression.tbd", "libsqlite3.tbd",
                 "libxml2.tbd", "libxml2.2.tbd", "libbz2.tbd", "libbz2.1.0.tbd", "libicucore.tbd",
                 "libicucore.A.tbd", "libgcc_s.1.tbd", "libcurses.tbd", "libncurses.tbd"]

STANDARD_FRAMEWORKS = ["CoreFoundation", "Foundation", "CoreServices", "Security", "IOKit",
                       "ApplicationServices", "CoreGraphics", "ImageIO"]
GRAPHICS_FRAMEWORKS = ["Cocoa", "AppKit", "CoreAudio", "AudioToolbox", "CoreVideo", "OpenGL",
                       "Metal", "QuartzCore", "ForceFeedback", "Carbon", "CoreHaptics",
                       "GameController", "CoreMedia", "CoreText", "CoreImage", "CoreData",
                       "AudioUnit", "CoreAudioTypes", "CoreMIDI", "UniformTypeIdentifiers"]


PROFILES = {
    "macos": {"sdk": "macosx", "rt": "libclang_rt.osx.a", "std_frameworks": None, "gfx_frameworks": None,
              "cmake": []},
    "ios": {"sdk": "iphoneos", "rt": "libclang_rt.ios.a",
            "std_frameworks": ["CoreFoundation", "Foundation", "Security", "CoreGraphics", "ImageIO",
                               "MobileCoreServices", "SystemConfiguration"],
            "gfx_frameworks": ["UIKit", "OpenGLES", "Metal", "QuartzCore", "AVFoundation", "AVFAudio",
                               "AudioToolbox", "CoreAudio", "CoreAudioTypes", "CoreVideo", "CoreMotion",
                               "CoreHaptics", "GameController", "CoreMedia", "CoreText", "CoreImage",
                               "CoreBluetooth", "UniformTypeIdentifiers"],
            "cmake": ["-DCMAKE_SYSTEM_NAME=iOS", "-DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY"]},
    "iossim": {"sdk": "iphonesimulator", "rt": "libclang_rt.iossim.a", "std_frameworks": None,
               "gfx_frameworks": None,
               "cmake": ["-DCMAKE_SYSTEM_NAME=iOS", "-DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY"]},
}
PROFILES["iossim"]["std_frameworks"] = PROFILES["ios"]["std_frameworks"]
PROFILES["iossim"]["gfx_frameworks"] = PROFILES["ios"]["gfx_frameworks"]
PROFILES["macos"]["std_frameworks"] = STANDARD_FRAMEWORKS
PROFILES["macos"]["gfx_frameworks"] = GRAPHICS_FRAMEWORKS


def capture(cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()


def flatten_framework(src, dst):
    version = os.path.join(src, "Versions", "A")
    base = version if os.path.isdir(version) else src
    name = os.path.basename(src)[:-len(".framework")]
    os.makedirs(dst, exist_ok=True)
    headers = os.path.join(base, "Headers")
    if os.path.isdir(headers):
        shutil.copytree(headers, os.path.join(dst, "Headers"), symlinks=False, ignore=IGNORE)
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


def collect_base(sdk, out, rt_name, std_frameworks):
    inc = os.path.join(sdk, "usr", "include")
    std_inc = os.path.join(out, "standard", "include")
    os.makedirs(std_inc)
    for name in sorted(os.listdir(inc)):
        if name in SKIP_INCLUDE or name.startswith(SKIP_PREFIXES) or name.startswith(".") or name.endswith(SKIP_SUFFIXES):
            continue
        src = os.path.join(inc, name)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(std_inc, name), symlinks=False, ignore=IGNORE)
        else:
            shutil.copy2(src, std_inc)
    cxx = os.path.join(inc, "c++")
    if not os.path.isdir(cxx):
        sys.exit("libc++ headers not found in the SDK")
    shutil.copytree(cxx, os.path.join(out, "runtime", "include", "c++"), symlinks=False, ignore=IGNORE)

    std_lib = os.path.join(out, "standard", "lib")
    rt_lib = os.path.join(out, "runtime", "lib")
    os.makedirs(std_lib)
    os.makedirs(rt_lib)
    ulib = os.path.join(sdk, "usr", "lib")
    for path in sorted(glob.glob(os.path.join(ulib, "*.tbd"))):
        name = os.path.basename(path)
        if name in RUNTIME_LIBS:
            shutil.copy2(path, os.path.join(rt_lib, name))
        elif name in STANDARD_LIBS:
            shutil.copy2(path, os.path.join(std_lib, name))
    system = os.path.join(ulib, "system")
    if os.path.isdir(system):
        shutil.copytree(system, os.path.join(std_lib, "system"), symlinks=False, ignore=IGNORE)
    if not os.path.exists(os.path.join(std_lib, "libSystem.tbd")):
        sys.exit("libSystem.tbd not found")

    resource = capture(["clang", "-print-resource-dir"])
    rt = os.path.join(resource, "lib", "darwin", rt_name)
    if not os.path.isfile(rt):
        sys.exit("not found: " + rt)
    shutil.copy2(rt, rt_lib)

    copy_frameworks(sdk, std_frameworks, os.path.join(out, "standard", "Frameworks"))


def collect_graphics(sdk, arch, out, work, profile):
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
                "-DCMAKE_OSX_SYSROOT=" + sdk] + profile["cmake"] + [
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
    copy_frameworks(sdk, profile["gfx_frameworks"], os.path.join(gfx, "Frameworks"))


def build(arch, out, work, platform="macos"):
    profile = PROFILES[platform]
    for d in (out, work):
        if os.path.exists(d):
            shutil.rmtree(d)
    os.makedirs(work)
    sdk = os.path.realpath(capture(["xcrun", "--sdk", profile["sdk"], "--show-sdk-path"]))
    print("sdk: " + sdk, flush=True)
    collect_base(sdk, out, profile["rt"], profile["std_frameworks"])
    collect_graphics(sdk, arch, out, work, profile)
    with open(os.path.join(out, "SOURCE.txt"), "w") as f:
        f.write("Apple SDK: " + os.path.basename(sdk) + "\narch " + arch + "\nSDL2 " + SDL2_VERSION +
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
