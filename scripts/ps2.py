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


def build(env_dir, out, source):
    if os.path.exists(out):
        shutil.rmtree(out)
    copy_parts(os.path.join(env_dir, "ps2sdk"), os.path.join(out, "standard"), STANDARD, STANDARD_REQUIRED)
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
