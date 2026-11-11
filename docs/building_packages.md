# Building the packages

The packages are built in GitHub Actions by the workflow **Build SDK packages** (`.github/workflows/build-sdks.yml`). It runs only when started by hand.

## Running the workflow

1. Open the **Actions** tab of the repository.
2. Select **Build SDK packages** and press **Run workflow**.
3. Fill in the inputs if needed.

| Input | Meaning |
| --- | --- |
| `only` | Build only this package id, for example `android-arm64-v8a`. Empty builds all packages. |
| `release_tag` | Upload to this release tag. Empty uses the latest release, and creates `v1.0.0` when the repository has no release yet. |

## What the workflow does

1. **plan** reads the list of packages and prepares one job per package.
2. **build** runs the job of each package on the right runner. It collects the SDK with the script of the target in `scripts/`, packs it into `rebax-sdk-<id>.tar.xz`, and uploads the package and its checksum as artifacts. The Android jobs also compile the SDL2 Java sources into `graphics/dex/classes.dex`.
3. **trees** merges the file listings of all packages into one artifact named `trees-all`. Open it to check what each package contains.
4. **release** uploads the packages and an updated `manifest.json` to the release. Packages that were not rebuilt keep their entries in the manifest.

## Checking a package

Download `trees-all` from the finished run. It contains one listing per package. For example, an Android package must contain `graphics/dex/classes.dex`, and a Windows package must contain `graphics/lib` and `bin/SDL2.dll`.

## Adding a target

1. Describe the new target in `scripts/common.py`.
2. Add or reuse a script in `scripts/` that collects the SDK into the output folder using the `standard`, `runtime` and `graphics` layout.
3. Run the workflow with `only` set to the new id.
4. Add the id to the package list of Rebax so it appears in the package window.
