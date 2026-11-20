import argparse, os, shutil, subprocess, sys

GRAPHICS_HEADERS = ["psxgpu.h", "psxgte.h", "inline_c.h", "inline_s.inc", "gtereg.inc"]
GRAPHICS_LIBS = ("libpsxgpu_", "libpsxgte_")
VARIANTS = ["release", "debug"]


def run(cmd, cwd=None, env=None):
    print("+ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, cwd=cwd, env=env)


def fetch(version, work):
    toolchain = os.environ.get("REBAX_PS1_TOOLCHAIN")
    if not toolchain or not os.path.isfile(os.path.join(toolchain, "bin", "mipsel-none-elf-gcc")):
        sys.exit("REBAX_PS1_TOOLCHAIN must point to the Rebax PS1 compiler package")
    toolchain = os.path.abspath(toolchain)
    source = os.path.join(work, "PSn00bSDK")
    run(["git", "clone", "--recursive", "--depth", "1", "-b", "v" + version,
         "https://github.com/Lameguy64/PSn00bSDK.git", source])
    env = dict(os.environ)
    env["PATH"] = os.path.join(toolchain, "bin") + os.pathsep + env.get("PATH", "")
    env["CFLAGS"] = "-std=gnu17"
    build_dir = os.path.join(work, "build")
    run(["cmake", "-S", source, "-B", build_dir, "-G", "Ninja", "-DCMAKE_BUILD_TYPE=Release",
         "-DSKIP_EXAMPLES=ON", "-DMKPSXISO_NO_LIBFLAC=ON", "-DPSN00BSDK_TC=" + toolchain], env=env)
    run(["cmake", "--build", build_dir], env=env)
    root = os.path.join(build_dir, "tree")
    if not os.path.isdir(os.path.join(root, "lib", "libpsn00b", "release")):
        sys.exit("unexpected build layout: " + root)
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

    target_root = os.path.join(root, "mipsel-none-elf")
    if os.path.isdir(target_root):
        shutil.copytree(target_root, os.path.join(out, "standard", "mipsel-none-elf"), symlinks=True)
    gcc_root = os.path.join(root, "lib", "gcc", "mipsel-none-elf")
    if os.path.isdir(gcc_root):
        shutil.copytree(gcc_root, os.path.join(out, "standard", "lib", "gcc", "mipsel-none-elf"), symlinks=True)

    with open(os.path.join(out, "SOURCE.txt"), "w") as f:
        f.write("PSn00bSDK %s (built from source with the Rebax PS1 compiler)\n" % version)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--arg", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    build(a.arg, a.out)


if __name__ == "__main__":
    main()
