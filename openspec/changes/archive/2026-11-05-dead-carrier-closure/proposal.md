# Proposal

## Why

On 2026-11-05 the owner asked why `system/projections/` holds only a README. Commit `84dbbf755`
(2026-10-14) moved the drawing integration to architecture-publisher and deleted the directory's
only content. The README stayed, and configuration kept pointing at the empty directory. A
repository-wide audit then found the same defect class in 14 more places: configuration roots,
globs, control prefixes, a skill reference, a fixture, a dead reader and unread tables.

No existing check caught any of them, because every owner looked only at part of the problem:

- reference closure matched deleted paths by equality and only between `candidate/dev` and
  `HEAD`, so a reference to an emptied directory, or any reference after the lane landed, passed;
- docs health checked README-only directories under `docs/` only;
- `surfaces.schema.json` accepted keys that no reader consumes;
- format selection checked that each file sits under an allowed root, never that each root holds
  a file;
- the archived `dead-carriers` Change was a one-off inventory with no requirement.

## What Changes

- Reference closure holds every declared repository path to the content it names at `HEAD`. A
  path must be a tracked file, a directory that holds a tracked file other than a README, or a
  glob that matches one. The declaration owner names the fields that carry repository paths; shipped
  catalogs that name adopter paths have none.
- Reference closure matches a reference to a directory that retired files left empty as a
  consumer of those files. Deletion admission refuses a script input that names a directory whose
  every file the patch deletes.
- Docs health reports every tracked README outside `docs/` that is its directory's only file.
- The surfaces contract schema refuses unknown tables and surface fields.
- Format selection reports every policy root that admits no tracked file of its format.
- A `repository-governance` requirement makes the rule a ratchet.
- The instances are removed: `system/projections/` and its references, the `system/openspec/` and
  `.config/ci/` format roots, the JSONL `build/` root, `tools/ci/scripts/**` in `.ethos/rules.toml`,
  three control prefixes for removed directories, the stale test-gate path in the quality-gate
  skill, the unused `independent-verification-adopters` fixtures, the dead `emulator_*` reader,
  and the unread `[semantic_axes]` and `[extension_roots]` taxonomy tables.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: a declared path, a README, a contract key and a format root each must
  name content that exists and is read.

## Impact

- `src/ethos/repository/policy/references/` (closure, carriers, the new `declared_paths.py`,
  observation and declarations), `src/ethos/repository/registry/docs/health.py`,
  `src/ethos/adapters/admission/control/replacement.py` and `tools/ci/format_selection.py`.
- `system/surfaces.toml`, `system/schemas/contracts/surfaces.schema.json`, `system/README.md`,
  `.config/checks/format-selection/policy.toml`, `.ethos/rules.toml`, `docs/_meta/taxonomy.toml` and
  the quality-gate skill reference with its package digest.
- Tests for each rule, and the removed fixture directory.
