import argparse, hashlib, json, lzma, os, subprocess, sys, tarfile

TARGETS = [
    {"id": "linux-x86_64", "script": "linux", "arg": "x86_64", "platform": "linux/amd64"},
    {"id": "linux-arm64", "script": "linux", "arg": "arm64", "platform": "linux/arm64"},
    {"id": "linux-x86", "script": "linux", "arg": "x86", "platform": "linux/386"},
    {"id": "linux-arm", "script": "linux", "arg": "arm", "platform": "linux/arm/v7"},
    {"id": "macos-x86_64", "script": "macos", "arg": "x86_64", "runner": "macos-15"},
    {"id": "macos-arm64", "script": "macos", "arg": "arm64", "runner": "macos-15"},
    {"id": "ios-arm64", "script": "ios", "arg": "arm64", "runner": "macos-15"},
    {"id": "ios-simulator-x86_64", "script": "ios", "arg": "simulator-x86_64", "runner": "macos-15"},
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
        for entry in sorted(os.listdir(root)):
            tf.add(os.path.join(root, entry), arcname=entry)
    with open(os.path.join(dest, name + ".tree.txt"), "w", encoding="utf-8") as f:
        f.write(list_tree(root, top))
    digest = sha256(archive)
    with open(os.path.join(dest, name + ".sha256"), "w") as f:
        f.write(digest + "  " + name + ".tar.xz\n")
    print(name, os.path.getsize(archive), digest)


def manifest(directory):
    path = os.path.join(directory, "manifest.json")
    items = {}
    if os.path.isfile(path):
        with open(path) as f:
            items = json.load(f).get("packages", {})
    for fn in sorted(os.listdir(directory)):
        if fn.endswith(".tar.xz"):
            p = os.path.join(directory, fn)
            items[fn[:-7]] = {"file": fn, "size": os.path.getsize(p), "sha256": sha256(p)}
    with open(path, "w") as f:
        json.dump({"packages": dict(sorted(items.items()))}, f, indent=2)
    print(len(items), "packages")


def write_section_manifests(root):
    """Write local dependency metadata beside each SDK section.

    The engine treats header names as discovery keys and never requires a
    hand-maintained master header or library list.
    """
    for section in ("standard", "runtime", "graphics"):
        directory = os.path.join(root, section)
        if not os.path.isdir(directory):
            continue
        headers = {}
        include = os.path.join(directory, "include")
        if os.path.isdir(include):
            for base, _, files in os.walk(include):
                for name in files:
                    if name.endswith(('.h', '.hh', '.hpp', '.hxx')):
                        rel = os.path.relpath(os.path.join(base, name), include).replace(os.sep, '/')
                        headers[rel] = {"libraries": []}
                        headers.setdefault(name, {"libraries": []})
        libraries = []
        libdir = os.path.join(directory, "lib")
        if os.path.isdir(libdir):
            for base, _, files in os.walk(libdir):
                for name in files:
                    if name.endswith(('.a', '.so', '.dylib')):
                        libraries.append(os.path.relpath(os.path.join(base, name), libdir).replace(os.sep, '/'))
        if section == "graphics":
            for key in ("SDL.h", "SDL2/SDL.h"):
                if key in headers:
                    headers[key]["libraries"] = ["SDL2"]
        if section == "runtime":
            for key in headers:
                headers[key]["libraries"] = ["c++"] if key.endswith(('.hpp', '.hxx')) else []
        payload = {"format": 1, "section": section, "headers": headers,
                   "libraries": sorted(set(libraries)), "extra_compile_flags": [],
                   "extra_link_flags": []}
        with open(os.path.join(directory, "rebax-libs.manifest"), "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=True)


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
