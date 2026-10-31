import argparse, os, sys

import macos


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--arg", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--work", default="sdk-work")
    a = p.parse_args()
    platform = "iossim" if a.arg == "simulator-x86_64" else "ios"
    arch = a.arg.split("-", 1)[1] if a.arg.startswith("simulator-") else a.arg
    macos.build(arch, a.out, os.path.abspath(a.work), platform)


if __name__ == "__main__":
    main()
