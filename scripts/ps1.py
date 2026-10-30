import argparse, os, shutil, sys, urllib.request, zipfile

GRAPHICS_HEADERS = ["psxgpu.h", "psxgte.h", "inline_c.h", "inline_s.inc", "gtereg.inc"]
GRAPHICS_LIBS = ("libpsxgpu_", "libpsxgte_")
VARIANTS = ["release", "debug"]


def fetch(version, work):
    url = "https://github.com/Lameguy64/PSn00bSDK/releases/download/v%s/PSn00bSDK-%s-Linux.zip" % (version, version)
    archive = os.path.join(work, "psn00bsdk.zip")
    print("download " + url, flush=True)
    urllib.request.urlretrieve(url, archive)
    with zipfile.ZipFile(archive) as z:
        z.extractall(work)
    root = os.path.join(work, "PSn00bSDK-%s-Linux" % version)
    if not os.path.isdir(os.path.join(root, "lib", "libpsn00b")):
        sys.exit("unexpected release layout: " + root)
    return root


def copy_file(src, dst_dir):
    os.makedirs(dst_dir, exist_ok=True)
    shutil.copy2(src, dst_dir)


def build(version, out):
    if os.path.exists(out):
        shutil.rmtree(out)
    work = os.path.abspath("ps1-work")
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    root = fetch(version, work)

    inc_src = os.path.join(root, "include", "libpsn00b")
    std_inc = os.path.join(out, "standard", "include", "libpsn00b")
    gfx_inc = os.path.join(out, "graphics", "include", "libpsn00b")
    shutil.copytree(inc_src, std_inc, symlinks=True, ignore=shutil.ignore_patterns(*GRAPHICS_HEADERS))
    for name in GRAPHICS_HEADERS:
        copy_file(os.path.join(inc_src, name), gfx_inc)

    lib_src = os.path.join(root, "lib", "libpsn00b")
    std_lib = os.path.join(out, "standard", "lib", "libpsn00b")
    gfx_lib = os.path.join(out, "graphics", "lib", "libpsn00b")
    for variant in VARIANTS:
        for name in sorted(os.listdir(os.path.join(lib_src, variant))):
            target = gfx_lib if name.startswith(GRAPHICS_LIBS) else std_lib
            copy_file(os.path.join(lib_src, variant, name), os.path.join(target, variant))
    shutil.copytree(os.path.join(lib_src, "ldscripts"), os.path.join(std_lib, "ldscripts"))

    with open(os.path.join(out, "SOURCE.txt"), "w") as f:
        f.write("PSn00bSDK %s (libraries built with gcc 12.3.0 mipsel-none-elf)\n" % version)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--arg", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    build(a.arg, a.out)


if __name__ == "__main__":
    main()
