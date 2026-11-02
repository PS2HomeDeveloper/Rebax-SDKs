import argparse, os, shutil, sys

STANDARD = [
    "common/include",
    "ee/include",
    "ee/lib",
    "ee/startup",
    "iop/include",
    "iop/lib",
    "iop/startup",
    "iop/irx",
]
STANDARD_REQUIRED = ["common/include", "ee/include", "ee/lib", "ee/startup"]
GRAPHICS = ["include", "lib"]


def copy_parts(src_root, dst_root, parts, required):
    for part in parts:
        src = os.path.join(src_root, part)
        if not os.path.isdir(src):
            if part in required:
                sys.exit("missing required folder: " + src)
            print("skip (not found): " + part)
            continue
        shutil.copytree(src, os.path.join(dst_root, part), symlinks=True,
                        ignore=shutil.ignore_patterns("pkgconfig"))
        print("copied: " + part)


EE_TRIPLE = "mips64r5900el-ps2-elf"


def copy_libc(env_dir, dst_root):
    base = os.path.join(env_dir, "ee", EE_TRIPLE)
    for name, skip in (("include", ("c++",)), ("lib", ("ldscripts", "libstdc++*", "libsupc++*", "libatomic*", "crt0.o"))):
        src = os.path.join(base, name)
        fixed = shutil.ignore_patterns(*skip)

        def ignore(folder, names, src_dir=src, fixed=fixed):
            gone = set(fixed(folder, names))
            gone.update(n for n in names if os.path.islink(os.path.join(folder, n)))
            return gone

        if not os.path.isdir(src):
            sys.exit("missing newlib folder: " + src)
        shutil.copytree(src, os.path.join(dst_root, name), symlinks=True, ignore=ignore)
        print("copied: libc/" + name)
    if not os.path.isfile(os.path.join(dst_root, "lib", "libc.a")):
        sys.exit("libc.a not found")


def build(env_dir, out, source):
    if os.path.exists(out):
        shutil.rmtree(out)
    copy_parts(os.path.join(env_dir, "ps2sdk"), os.path.join(out, "standard"), STANDARD, STANDARD_REQUIRED)
    copy_libc(env_dir, os.path.join(out, "standard", "libc"))
    copy_parts(os.path.join(env_dir, "gsKit"), os.path.join(out, "graphics"), GRAPHICS, GRAPHICS)
    with open(os.path.join(out, "SOURCE.txt"), "w") as f:
        f.write("ps2dev image: " + source + "\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--arg", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--source", default="unknown")
    a = p.parse_args()
    build(a.arg, a.out, a.source)


if __name__ == "__main__":
    main()
