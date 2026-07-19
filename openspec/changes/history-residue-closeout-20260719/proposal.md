## Why

The product checkout carries tracked work notes, mixed-generation configuration,
unbounded local proof records, obsolete SQLite schema, orphan Lane leases, and an
unclosed recovery snapshot set. On July 19, 2026 the source-budget gate also
reports ten expired debt records and seven budget overruns, so residue is both a
local hygiene problem and an active governance failure.

## What Changes

- Remove tracked work notes that explicitly declare themselves non-truth, while
  preserving any still-required historical claim linkage in canonical history.
- Convert `.ethos/rules.toml` to the current rule shape without losing quality,
  gate, or source-budget policy, and remove stale evidence-root declarations.
- Retire dead projection and release fields together with adopter scaffold
  projections so new repositories do not recreate the residue.
- Add versioned SQLite local-state migration and deterministic maintenance for
  obsolete tables, expired orphan leases, and HEAD-keyed proof retention.
- Preserve the July 9 recovery bundles through a digest-bound receipt and a
  durable operator archive before removing duplicate disposable snapshots.
- Settle expired source-budget debt through real carrier deletion or
  consolidation; do not reset the baseline, erase debt, or extend expiry merely
  to obtain a green result.
- Add focused tests, OpenSpec deltas, Chronicle evidence, and HEAD-bound proof for
  every cleanup boundary.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-governance`: subject=local-state-history-residue-closeout;
  reuse=extend; change=modify; facet:lifecycle=validation,runtime,archive;
  facet:surface=cli,docs,openspec,evidence; facet:authority=source,test,openspec,evidence,claim.
- `quality`: subject=expired-source-budget-and-rules-v2-closeout; reuse=extend;
  change=modify; facet:lifecycle=authoring,validation,release;
  facet:surface=cli,test,openspec,evidence; facet:authority=source,test,openspec,evidence,claim.
- `assistant-projections`: subject=retired-root-assistant-projection;
  reuse=extend; change=remove; facet:lifecycle=authoring,validation;
  facet:surface=scaffold,test,openspec; facet:authority=source,test,openspec.
- `distribution`: subject=retired-release-configuration-fields; reuse=extend;
  change=remove; facet:lifecycle=authoring,validation,release;
  facet:surface=scaffold,package,test,openspec; facet:authority=source,test,openspec.
- `adapters`: subject=operator-supplied-independent-verification-executables;
  reuse=extend; change=modify; facet:lifecycle=validation,runtime,release;
  facet:surface=package,test,docs,openspec; facet:authority=source,test,openspec,evidence.

## Out Of Scope

- Remote push, hosted CI, hosted publication, credentials, or provider-side
  mutation.
- Deletion of current-HEAD proof, unexpired leases, the entire SQLite database,
  or recovery material before archive verification.
- Source-budget baseline reset, terminal-target relaxation, silent expiry
  rollover, or a replacement umbrella debt record.
- A new truth store, assistant authority surface, or second governance command
  plane.

## Impact

Affected surfaces include `.ethos/*.toml`, ignored `.ethos/state/`, adopter
scaffold templates and manifests, rule migration, SQLite state adapters, proof
storage, quality/source-budget reporting, release policy, assistant projection
contracts, tests, canonical documentation, claims, Chronicle evidence, and the
OpenSpec specifications named above. The public transition command shape remains
unchanged, while closeout admission is strengthened to fail closed on unavailable
control diffs, control-path removal or rename, candidate-HEAD drift, and
candidate-local bootstrap artifacts. Mutation remains Work-Lane-bound and
local-state cleanup remains non-authoritative.
