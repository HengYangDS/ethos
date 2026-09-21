## Context

Architecture Publisher owns generic source, Claim Model, Edition, scene,
qualification, and publication contracts. ETHOS owns the meaning projected from
`system/projections/terminal-architecture`, plus all repository authority and
effects. The current `migration/ethos` package in Architecture Publisher is a
bounded staging copy, not a valid terminal owner.

## Decision

Create `integrations/architecture-publisher` as the sole mutable ETHOS-owned npm
package `@architecture-publisher/ethos`.

The package boundary is:

```text
ETHOS source and accepted projection
  -> exact portable ETHOS projection
  -> @architecture-publisher/ethos adapter
  -> Architecture Publisher Claim Model and Edition
  -> public Architecture Publisher compilers/renderers
  -> exact Candidate and sibling media
```

The integration imports only exported `architecture-publisher` package
contracts. It has no dependency on ETHOS Python internals and no right to mutate
the repository. Conversely, the generic Publisher package contains no ETHOS
branching or schema knowledge.

The package is not an ETHOS root command and is not loaded by default. Its
manifest declares the compatible Publisher version; conformance installs exact
local package archives together in an isolated directory. Runtime behavior uses
only explicit paths and digests. Repository-relative paths are permitted only in
authoring and tests before packaging; installed execution receives portable
inputs.

Installed conformance resolves exported package specifiers through Node rather
than importing internal source-file URLs as public entrypoints. Candidate and
sibling-media delivery consume the existing input-file APIs; intermediate model
comparisons remain explicitly white-box. A missing export target must reject
installation qualification even when its former internal implementation exists.

## Physical ownership

```text
integrations/architecture-publisher/
  package.json
  README.md
  src/
    adapter/
    edition/
    runtime.mjs
tests/architecture/
  architecture-publisher-integration.test.mjs
  architecture-publisher-installed.test.mjs
```

The existing `system/projections/terminal-architecture` remains the source
projection owner. Generated diagrams, Candidate bundles, browser observations,
and parity results stay below ignored build roots or compact digest-only evidence;
large generated media do not enter Git history.

## Migration and parity

1. Record the exact Publisher source commit and migration-package tree digest.
2. Copy the migration package once into the ETHOS-owned integration and remove
   migration-only wording.
3. Add ETHOS-local tests for projection intake, semantic preservation, Edition
   construction, candidate preparation, static/interactive generation, and
   absence of governance effects.
4. Pack Publisher core and both ETHOS packages independently, install them in
   relocated empty homes, and compare Candidate, static, and interactive digests.
5. If bytes differ, classify the difference. Semantic differences require
   explicit successor review; packaging-only differences must not alter the
   Candidate.
6. After parity, retain the ETHOS package here and a compact immutable conformance
   fixture in Publisher, then delete Publisher's mutable migration package and
   ETHOS-specific implementation tests.

## Quality and dependency policy

JavaScript formatting and syntax remain under existing native Node/Prettier
owners. Python gates remain unchanged. The package adds no daemon, database,
workflow ledger, CLI alias, compatibility facade, repository discovery, or
implicit network access. A package/test integration enters the existing quality
graph rather than defining another gate registry.

## Failure and rollback

Before Publisher removes its staging copy, rollback is deletion of this Work
Lane. After parity and cross-repository handoff, each repository remains
independently reversible through its own Git history. A failed parity run changes
neither accepted source nor release artifacts. Missing Publisher packages,
credentials, or remote access block only their dependent proof; ordinary ETHOS
behavior remains available.

## Acceptance and closeout

Implementation tasks finish before the lifecycle effects they enable. A task
cannot require this Change to be archived before archive admission, nor append
an exact-proof result to the very source snapshot that result verifies.
Completing the task list does not establish accepted integration or retirement.

After the implementation snapshot is frozen, require the complete ETHOS proof
graph on that exact HEAD. Follow fresh native admission for official OpenSpec
archive, any required postarchive proof, and integration through `candidate/dev`
into `dev`. Read back accepted source/tree and signatures, then perform normal
landed retirement of the absorbed Lane with its unique history retained.
The carrier Lane still supports other active Changes; close its Lease and retire
it only when those obligations are complete. Never retire it merely because
this integration package is ready.

Closeout requires observed official archive, accepted integration, clean retained
worktrees, valid signatures, closed retired-Lane Leases and no associated
proposal or disposable residue. Native results and exact evidence own these
facts; neither checked tasks nor package parity prove them. Preserve failures
and unproved external limits. Do not add a second ledger, relax archive
readiness or recognize special task wording to bypass these conditions.
