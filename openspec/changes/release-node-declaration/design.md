# Design

## Context

See [proposal.md](proposal.md). `tools/ci/release_supply_chain.py` runs one Syft scan over the
runtime archive that the install smoke kept. `missing_components` then compares the catalog with the
runtime manifest: each shipped Python distribution, each bundled Go tool, uv and Node. The Node
payload keeps `node.exe` as the official archive ships it (`_retain_native_payload` in
`src/ethos/adapters/repo/runtime/materialization/node/supply.py`). `materialize_tool(ROOT, "node")`
returns that payload after verifying the archive against `mise.lock`.

## Goals / Non-Goals

Goals:

- Every runtime archive's inventories name Node at its locked version, on every platform.
- A declaration is bound to the shipped bytes. It cannot name a file that differs from the locked
  supply.
- A reader can tell which components ETHOS declared and which the catalog found.

Non-goals:

- Declaring components that ETHOS does not lock. A missing Python distribution, Go module or uv
  crate still refuses.
- Patching Syft or replacing it as the cataloger.

## Decisions

- **Declare from the supply, not from a second scan.** Renaming or copying `node.exe` so that Syft
  matches it would scan bytes at a path the archive does not have. The locked supply already states
  the version, and the digest comparison binds that statement to the shipped file.
- **Use Syft's identity fields.** The beta.3 linux-x64 inventories record Node as a `binary`
  artifact with purl `pkg:generic/node@<version>`, CPE `cpe:2.3:a:nodejs:node.js:<version>:*:*:*:*:*:*:*`
  (source `nvd-cpe-dictionary`) and a location, contained by the source and evident by its file. The
  declaration uses the same fields, so Grype matches it as it matches Syft's record. It has no
  binary-signature metadata, because no signature matched; `foundBy` is `ethos-locked-supply`. The
  file entry loses Syft's "no package identified" note, as a file whose package Syft found does. The
  SPDX package adds the SHA-256 checksum and a `sourceInfo` naming the locked supply, with `CONTAINS`
  from the document root, `evident-by` to the file and ETHOS among the creators.
- **Bind to the archive's platform.** The locked supply that vouches is the one whose target is the
  archive's runtime platform. A Windows on Arm leg builds an x64 runtime, and its x64 interpreter
  selects the x64 supply; a supply for any other platform refuses.
- **One definition of a gap.** The owner declares Node only when `missing_components` reports it
  missing, so the declaration lapses when Syft classifies `node.exe`. A test pins the locked Syft
  version: a new Syft fails it until someone checks `node.exe` again and removes the declaration
  path or moves the pinned version.
- **Node only.** Node is the one locked executable that the catalog misses today, so the owner
  declares Node and nothing else. A second component would get its own declaration when a catalog
  gap shows one.

## Risks / Trade-offs

- If the build ever rewrote the Node executable, for example by signing or stripping it, the digests
  would differ and the release would refuse. That is the intended failure, and every Windows
  host-conformance run on Python 3.14 exercises it.
- An SBOM that mixes cataloged and declared records depends on readers honoring `foundBy` and
  `sourceInfo`. The supply-chain evidence repeats the declared list for readers that do not.
