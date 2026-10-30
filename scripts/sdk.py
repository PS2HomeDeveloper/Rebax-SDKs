import argparse, hashlib, json, lzma, os, shutil, sys, tarfile

PS2_STANDARD = [
    "common/include",
    "ee/include",
    "ee/lib",
    "ee/startup",
    "iop/include",
    "iop/lib",
    "iop/startup",
    "iop/irx",
]
PS2_STANDARD_REQUIRED = ["common/include", "ee/include", "ee/lib", "ee/startup"]
PS2_GRAPHICS = ["include", "lib"]
PS2_GRAPHICS_REQUIRED = ["include", "lib"]


def copy_parts(src_root, dst_root, parts, required):
    for part in parts:
        src = os.path.join(src_root, part)
        if not os.path.isdir(src):
            if part in required:
                sys.exit("missing required folder: " + src)
            print("skip (not found): " + part)
            continue
        shutil.copytree(src, os.path.join(dst_root, part), symlinks=True)
        print("copied: " + part)


def cmd_ps2(a):
    if os.path.exists(a.out):
        shutil.rmtree(a.out)
    copy_parts(os.path.join(a.ps2dev, "ps2sdk"), os.path.join(a.out, "standard"), PS2_STANDARD, PS2_STANDARD_REQUIRED)
    copy_parts(os.path.join(a.ps2dev, "gsKit"), os.path.join(a.out, "graphics"), PS2_GRAPHICS, PS2_GRAPHICS_REQUIRED)
    with open(os.path.join(a.out, "SOURCE.txt"), "w") as f:
        f.write("ps2dev image: " + a.source + "\n")


def list_tree(root):
    lines = []
    for base, dirs, files in os.walk(root):
        dirs.sort()
        rel = os.path.relpath(base, root)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        if rel != ".":
            lines.append("  " * depth + os.path.basename(base) + "/")
        for f in sorted(files):
            p = os.path.join(base, f)
            if os.path.islink(p):
                lines.append("  " * (depth + 1) + f + " -> " + os.readlink(p))
            else:
                lines.append("  " * (depth + 1) + f + "  (" + str(os.path.getsize(p)) + " bytes)")
    return "\n".join(lines) + "\n"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def cmd_pack(a):
    os.makedirs(a.dest, exist_ok=True)
    archive = os.path.join(a.dest, a.name + ".tar.xz")
    with tarfile.open(archive, "w:xz", preset=9 | lzma.PRESET_EXTREME) as tf:
        tf.add(a.root, arcname=a.top)
    with open(os.path.join(a.dest, a.name + ".tree.txt"), "w", encoding="utf-8") as f:
        f.write(a.top + "/\n" + list_tree(a.root))
    digest = sha256(archive)
    with open(os.path.join(a.dest, a.name + ".sha256"), "w") as f:
        f.write(digest + "  " + a.name + ".tar.xz\n")
    print(a.name, os.path.getsize(archive), digest)


def cmd_manifest(a):
    items = {}
    for fn in sorted(os.listdir(a.dir)):
        if fn.endswith(".tar.xz"):
            p = os.path.join(a.dir, fn)
            items[fn[:-7]] = {"file": fn, "size": os.path.getsize(p), "sha256": sha256(p)}
    with open(os.path.join(a.dir, "manifest.json"), "w") as f:
        json.dump({"packages": items}, f, indent=2)
    print(len(items), "packages")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("ps2")
    s.add_argument("--ps2dev", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--source", default="unknown")
    k = sub.add_parser("pack")
    k.add_argument("--root", required=True)
    k.add_argument("--top", default="sdk")
    k.add_argument("--name", required=True)
    k.add_argument("--dest", required=True)
    m = sub.add_parser("manifest")
    m.add_argument("--dir", required=True)
    a = p.parse_args()
    {"ps2": cmd_ps2, "pack": cmd_pack, "manifest": cmd_manifest}[a.cmd](a)


if __name__ == "__main__":
    main()
