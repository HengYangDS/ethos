# Design

## Context

See [proposal.md](proposal.md), and the reviewed design in
`build/runtime/work/beta2/grype-design-draft.md`, decision of 2026-11-05 01:05.

The install smoke keeps each built runtime archive at `build/artifacts/native/<runtime>/` and
records its SHA-256 in `build/evidence/local-install/smoke.json`, or `release-smoke.json` in a
release leg. The release legs have no write permission. `release-publish` assembles the qualified
archives with `release_assets.py`, attests them with `actions/attest-build-provenance` and creates
the release.

## Goals / Non-Goals

Goals:

- Every published runtime archive declares its components in inventories that are bound to its
  bytes, checked for completeness against their owners, and attested with it.
- One SBOM producer, the existing `release-sbom` owner.

Non-goals:

- Scanning the inventories, which Change `release-binary-scan` adds.
- An SBOM attestation predicate. `actions/attest-sbom` is deprecated, and provenance over the
  inventory files binds them to the release workflow.

## Decisions

1. **Subject.** `release_supply_chain.py` reads the smoke record and finds the archive it
   names. It requires the archive's bytes to match the recorded SHA-256. The published name is
   `ethos-<product version>-<host>.tar.gz`. A release leg passes `--host` for its declared host;
   a proof uses the runtime's own platform.
2. **One Syft run, explicit configuration.** `syft scan file:<archive>` runs with
   `--source-name <name>` and `--config <file>`, and writes two outputs:
   - `build/evidence/release/runtime.spdx.json`;
   - `build/evidence/release/runtime.syft.json`.

   The configuration comes from the policy's `[syft_config]`: no update check, and
   `golang.capture-symbols = "extended-stdlib"`. Inherited `SYFT_` variables are removed. Syft
   computes the archive's digest itself, so the inventories name the bytes they read.

3. **Why two formats.** SPDX cannot carry symbols. On the alpha.29 macOS archive, Grype matches
   113 advisory pairs over the SPDX, but exactly the 63 of a direct `dir:` scan over the
   symbol-capturing Syft JSON (`build/runtime/work/grype/lane/acceptance/`).
4. **Completeness from owners.** The expected components are:
   - for every native Go tool under `ethos/resources/native/` that the native supply declares,
     a Go main module at its declared version, located at that executable;
   - for the `uv` distribution's executable, the `uv` crate at the locked version;
   - for the supplied Node executable, Node at the supplied version;
   - for every `*.dist-info` that the runtime manifest lists, that distribution.

   Missing ones are named as `release_inventory_component_missing:<kind>:<name>@<version>`.

5. **Admission at publication.** `release_assets.inventory_gaps` is one standard-library rule,
   shared by the producer and the assembler:
   - the SPDX `DESCRIBES` root has the published name and the archive's SHA-256;
   - the Syft JSON source has the same name and digest;
   - each lists components.

   The assembler reads each host's two inventories as single regular files under 16 MB, and
   publishes them as `ethos-<version>-<host>.spdx.json` and `.syft.json`. A required host whose
   inventories are missing or invalid stops the release. A Windows host without inventories is
   left out, as the platform requirement allows.

6. **Attestation.** The existing `attest-build-provenance` step covers both inventory files.

## Risks / Trade-offs

- Each release gains about 12 MB of inventories per archive, measured on the alpha.29 macOS
  archive: 5.3 MB of SPDX and 6.8 MB of Syft JSON.
- The proof's `release-sbom` gate now waits for `local-install-smoke`, and cataloging takes about
  20 seconds.
