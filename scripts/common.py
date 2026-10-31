import argparse, hashlib, json, lzma, os, subprocess, sys, tarfile

TARGETS = [
    {"id": "ps2", "script": "ps2", "arg": "ps2dev-env"},
    {"id": "ps1", "script": "ps1", "arg": "0.24"},
    {"id": "windows-x86_64", "script": "windows", "arg": "x86_64"},
    {"id": "windows-x86", "script": "windows", "arg": "x86"},
    {"id": "windows-arm", "script": "windows", "arg": "arm"},
    {"id": "windows-arm64", "script": "windows", "arg": "arm64"},
    {"id": "android-arm64-v8a", "script": "android", "arg": "arm64-v8a"},
    {"id": "android-armeabi-v7a", "script": "android", "arg": "armeabi-v7a"},
    {"id": "android-x86", "script": "android", "arg": "x86"},
    {"id": "android-x86_64", "script": "android", "arg": "x86_64"},
]


def run(cmd, **kw):
    print("+ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, **kw)


def list_tree(root, top):
    state = {"dirs": 0, "files": 0}
    lines = [top]

    def walk(path, prefix):
        names = sorted(os.listdir(path))
        for i, name in enumerate(names):
            full = os.path.join(path, name)
            last = i == len(names) - 1
            branch = "└── " if last else "├── "
            if os.path.islink(full):
                lines.append(prefix + branch + name + " -> " + os.readlink(full))
                state["files"] += 1
            elif os.path.isdir(full):
                lines.append(prefix + branch + name)
                state["dirs"] += 1
                walk(full, prefix + ("    " if last else "│   "))
            else:
                lines.append(prefix + branch + name)
                state["files"] += 1

    walk(root, "")
    lines.append("")
    lines.append("%d directories, %d files" % (state["dirs"], state["files"]))
    return "\n".join(lines) + "\n"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pack(root, top, name, dest):
    os.makedirs(dest, exist_ok=True)
    archive = os.path.join(dest, name + ".tar.xz")
    with tarfile.open(archive, "w:xz", format=tarfile.GNU_FORMAT, dereference=True, preset=9 | lzma.PRESET_EXTREME) as tf:
        tf.add(root, arcname=top)
    with open(os.path.join(dest, name + ".tree.txt"), "w", encoding="utf-8") as f:
        f.write(list_tree(root, top))
    digest = sha256(archive)
    with open(os.path.join(dest, name + ".sha256"), "w") as f:
        f.write(digest + "  " + name + ".tar.xz\n")
    print(name, os.path.getsize(archive), digest)


def manifest(directory):
    items = {}
    for fn in sorted(os.listdir(directory)):
        if fn.endswith(".tar.xz"):
            p = os.path.join(directory, fn)
            items[fn[:-7]] = {"file": fn, "size": os.path.getsize(p), "sha256": sha256(p)}
    with open(os.path.join(directory, "manifest.json"), "w") as f:
        json.dump({"packages": items}, f, indent=2)
    print(len(items), "packages")


def matrix(only):
    chosen = [t for t in TARGETS if not only or t["id"] == only]
    if not chosen:
        sys.exit("no target matches: " + only)
    line = "matrix=" + json.dumps({"include": chosen}, separators=(",", ":"))
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write(line + "\n")
    print(line)


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    k = sub.add_parser("pack")
    k.add_argument("--root", required=True)
    k.add_argument("--top", required=True)
    k.add_argument("--name", required=True)
    k.add_argument("--dest", required=True)
    m = sub.add_parser("manifest")
    m.add_argument("--dir", required=True)
    x = sub.add_parser("matrix")
    x.add_argument("--only", default="")
    a = p.parse_args()
    if a.cmd == "pack":
        pack(a.root, a.top, a.name, a.dest)
    elif a.cmd == "manifest":
        manifest(a.dir)
    else:
        matrix(a.only)


if __name__ == "__main__":
    main()
