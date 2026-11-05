# Proposal

## Why

Release run 42117725176 for `v0.2.0-beta.3` failed both Windows legs at "Declare the components of
the retained runtime archive" with `release_inventory_component_missing:node:node@26.13.0`, so beta.3
shipped no Windows runtime. Syft 1.56.0 classifies Node only in a file named `node`: its
`nodejs-binary` classifier's glob is `**/node`, while its Go and Firefox classifiers also match
`.exe` names. No Syft setting adds a glob or a classifier. The Windows archive ships
`ethos/resources/node/node.exe`, unchanged from the locked official Node archive, and its
inventories omit it.

## What Changes

- When the catalog lacks a locked component that the runtime ships, the inventory owner declares it
  in both inventories from ETHOS's locked supply. Today that component is Node. The owner declares it
  only if the shipped file's SHA-256 equals the locked supply's executable on that host. Otherwise it
  refuses with `release_inventory_component_unverified:<component>`.
- A declared component mirrors Syft's own record (type, name, version, purl, CPE and location) and
  says that ETHOS declared it: `foundBy` in the Syft JSON inventory and `sourceInfo` in the SPDX
  SBOM. The supply-chain evidence lists declared components apart from cataloged ones.
- A component that the catalog already holds is never declared again, so the declaration lapses
  once Syft classifies `node.exe`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: a published runtime archive declares what it ships. A locked executable that the
  catalog misses is declared from its verified supply instead of failing the release.

## Impact

- `tools/ci/release_supply_chain.py` and its unit tests.
- Windows release legs and the Windows host-conformance legs that catalog their archives.
- The binary scan reads the declared Node through its CPE, as it reads Syft's own record.
- Out of scope: other catalogers, other components, and the upstream Syft change, which is filed
  separately with the owner's approval.
