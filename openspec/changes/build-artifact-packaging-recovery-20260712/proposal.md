## Why

The required `uv build --all-packages` proof gate can build the `ethos-core`
source distribution but fails while building its wheel: wheel force-includes
refer to paths outside the unpacked source distribution.

## What Changes

- Keep canonical declarations under `system/` in the checkout.
- Keep the sdist mapping that projects those declarations into
  `src/ethos_core/data/`.
- Make the wheel mapping consume those sdist-local projections rather than a
  checkout-relative path that is absent in the sdist build root.
- Assert the paired sdist and wheel mappings for every packaged declaration.
- Reallocate four existing candidate-train product-Python allowance lines to
  YAML metadata, preserving the immutable global source-budget cap.

## Out Of Scope

- Duplicating declaration files in the tracked package source.
- Changing runtime declaration lookup, package boundaries, releases, or remote
  publication.
