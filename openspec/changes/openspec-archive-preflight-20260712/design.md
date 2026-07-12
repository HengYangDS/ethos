## Context

OpenSpec's strict change validation checks delta syntax but intentionally does
not apply deltas to the current canonical specs. The official archive command
does that application atomically only at closeout. Consequently a change may
be valid in isolation but not archiveable against the current source tree.

The product must reveal this fact early without creating a second delta parser
or changing source files merely to inspect them.

## Decision

Lifecycle review materializes a disposable OpenSpec workspace under the system
temporary directory. It copies the source `openspec/` tree, runs the configured
official `openspec archive <change> --yes --json` command in that copy, collects
its JSON result, and removes the copy in all outcomes.

An archive failure becomes a change-scoped required gap with the official
diagnostic code, message, and suggested fix retained under
`archive_preflight`. A successful simulation is evidence that the current
source workspace is archiveable under the same official tool and options; it
does not archive the source, complete tasks, mint authority, or claim that a
later concurrent source change will remain archiveable.

## Invariants

- The source workspace is never passed to the preflight archive command.
- The official OpenSpec CLI remains the only owner of delta interpretation and
  archive application.
- Preflight uses the same configured official command path as lifecycle review.
- Temporary projection state is outside repository truth and is removed after
  the command returns.
- Official archive diagnostics remain attributable to the active change that
  produced them.
- The temporary source-budget debt records only this bounded implementation
  delta and expires when the official lifecycle API supplies an equivalent
  source-safe dry-run receipt.

## Alternatives Rejected

- **Hand-written delta collision parser:** incomplete as the official archive
  has multiple application-time rejection modes and may evolve independently.
- **Automatic delta rewrite:** silently changes the author's commitment and can
  turn an `ADDED`/`MODIFIED` mistake into an unjustified archive receipt.
- **Documentation only:** leaves normal proof and land paths able to reach the
  same deterministic late failure.

## Rollback

Remove the preflight projection and its lifecycle gap together. The official
archive and all tracked OpenSpec records remain unchanged by the feature.
