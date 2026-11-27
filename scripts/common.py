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
    """Write one readable manifest for every directory containing headers."""
    for name in sorted(os.listdir(root)):
        directory = os.path.join(root, name)
        include = os.path.join(directory, "include")
        if not os.path.isdir(directory) or not any(os.path.isdir(os.path.join(directory, child)) for child in ("include", "lib", "src")):
            continue
        headers = []
        for base, _, files in os.walk(include):
            for filename in sorted(files):
                if filename.endswith((".h", ".hh", ".hpp", ".hxx")):
                    headers.append(os.path.relpath(os.path.join(base, filename), include).replace(os.sep, "/"))
        libraries = []
        libdir = os.path.join(directory, "lib")
        if os.path.isdir(libdir):
            for base, _, files in os.walk(libdir):
                for filename in sorted(files):
                    if filename.endswith((".a", ".so", ".dylib", ".lib")):
                        libraries.append(os.path.relpath(os.path.join(base, filename), libdir).replace(os.sep, "/"))
        lib_names = []
        for library in libraries:
            stem = os.path.basename(library)
            if stem.startswith("lib"):
                stem = stem[3:]
            for suffix in (".a", ".so", ".dylib", ".lib"):
                if stem.endswith(suffix):
                    stem = stem[:-len(suffix)]
            if stem and stem not in lib_names:
                lib_names.append(stem)
        manifest = ["format=1", "section=" + name]
        if os.path.isdir(include):
            manifest.append("include=include")
        for header in headers:
            manifest.append("header=" + header + ("|" + ",".join(lib_names) if lib_names else ""))
        for library in libraries:
            manifest.append("library=" + library)
        with open(os.path.join(directory, "rebax-libs.manifest"), "w", encoding="utf-8") as f:
            f.write("\n".join(manifest) + "\n")


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
