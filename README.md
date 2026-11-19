# Rebax SDKs

Prebuilt target SDKs for the [Rebax Engine](https://github.com/PS2HomeDeveloper/Rebax).

Every package contains everything Rebax needs to compile a game for one target: the C library, the compiler runtime and the graphics library. The packages are built from upstream sources by GitHub Actions and published as release assets. Rebax downloads the ones it needs by itself, so most people never have to touch this repository.

## Packages

Each package is a single archive named `rebax-sdk-<id>.tar.xz` with one top folder named `<id>`.

| Target | Package ids |
| --- | --- |
| Android | `android-arm64-v8a`, `android-armeabi-v7a`, `android-x86`, `android-x86_64` |
| Linux | `linux-arm64`, `linux-arm`, `linux-x86`, `linux-x86_64` |
| Windows | `windows-arm64`, `windows-arm`, `windows-x86`, `windows-x86_64` |
| macOS | `macos-arm64`, `macos-x86_64` |
| iOS | `ios-arm64`, `ios-simulator-x86_64` |
| PlayStation 2 | `ps2` |
| PlayStation 1 | `ps1` |

The layout of a package is described in [docs/package_format.md](docs/package_format.md).

## Download

Packages are published in the latest release:

```
https://github.com/PS2HomeDeveloper/Rebax-SDKs/releases/latest/download/rebax-sdk-<id>.tar.xz
```

The release also contains `manifest.json`, which lists every package with its size and SHA-256 checksum. Rebax uses it to verify downloads.

## Manual installation

1. Download the package for your target from the latest release.
2. Extract it into the `sdks` folder of Rebax, so that the folder `sdks/<id>` exists.

Rebax treats a package as installed when its folder exists, so no other step is needed. To remove a package, delete its folder.

## Building the packages

The packages are built by the **Build SDK packages** workflow. See [docs/building_packages.md](docs/building_packages.md).

## PlayStation 2 network loader

The PlayStation 2 package also contains `ps2link/ps2link.elf`, built from the [ps2link](https://github.com/ps2dev/ps2link) sources with the high-memory layout. Rebax uses it to run projects on a real console over the network.

## Contributing

Issues and discussions for the whole project are in the [Rebax repository](https://github.com/PS2HomeDeveloper/Rebax). See [CONTRIBUTING.md](CONTRIBUTING.md) for changes to this repository.

## License

The scripts and documentation in this repository are released under the [MIT License](LICENSE). The packages contain software from other projects, each under its own license. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
