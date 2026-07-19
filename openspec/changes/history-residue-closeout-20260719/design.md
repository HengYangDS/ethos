## Context

The product Work Lane inherits two different kinds of residue. Tracked residue
includes non-authoritative work notes, legacy rule syntax, dead assistant and
release projections, and source-budget debt whose recorded expiry was July 18,
2026. Ignored local residue includes a version-1 SQLite database, leases that
outlived their Work Lanes, obsolete proof records, and July 9 recovery snapshots
that still contain Git objects unavailable from current refs.

The cleanup must respect three boundaries. First, `.ethos/state/` is local state,
not repository truth, so its maintenance cannot mint authority or silently alter
tracked claims. Second, tracked configuration and adopter scaffolds must change
together or new repositories will recreate the residue. Third, source-budget
debt is settled only by measured deletion or consolidation; changing the
baseline or administratively extending an expired record would hide rather than
close the debt.

## Goals / Non-Goals

**Goals:**

- remove tracked non-truth and dead projections without breaking the external
  runner marker or active release policy;
- make Rules V2 migration lossless for active quality policy and expose the
  already-advertised governed migration command;
- migrate existing SQLite state to schema version 2 without replacing the
  database or deleting active leases;
- provide explicit, deterministic maintenance for expired orphan leases and
  ref-unreachable proof records;
- move the complete recovery snapshot set into a digest-bound operator archive
  before deleting its disposable local-state copy;
- settle every debt record expired on July 18, 2026 through measured net
  deletion while preserving the immutable baseline and all unexpired debt;
- prove product/scaffold parity, focused behavior, full quality, and lifecycle
  readiness at the resulting Git HEAD.

**Non-Goals:**

- resetting source-budget baselines or terminal targets;
- extending an expiry only to make a gate pass;
- deleting the entire local-state database, current-HEAD proof, unexpired
  leases, or recovery material before preservation is verified;
- treating local maintenance output as hosted evidence or repository authority;
- adding a second governance command plane or making cleanup run implicitly from
  `status`, `orient`, `prove`, or normal lease reads.

## Decisions

### 1. Tracked cleanup is source/scaffold parity work

The product `.ethos` configuration and the adopter scaffold manifest/templates
will be updated in one change. `.ethos/assistants.toml` and its template/manifest
entry will be removed because assistant truth is already carried by repository
source, activation registries, schemas, and generated host projections. The
product project file will retain the externally consumed
`[command_plane].public = "ethos"` marker while removing duplicate state and
retired-command declarations. Release configuration will retain only fields
consumed by release policy; canonical artifact homes remain owned by generated
artifact topology rather than a dead `dist/*` glob.

Alternative considered: clean only the product checkout. Rejected because the
scaffold would immediately reproduce the same residue for adopters.

### 2. Rules migration is lossless and compare-and-swap guarded

Rules migration will normalize legacy `paths`, `requires`, and `evidence` keys
to V2 keys while preserving `[quality]`, `[standards]`, `[determinism]`,
`[formats]`, `[artifacts]`, and any other active non-rule policy. The stale
durable-evidence roots will be corrected to `evidence` and `evidence/claims`.
Adding V2 profiles and rule fields, rather than deleting still-consumed policy,
ends compatibility-only rule evaluation.
The public `ethos rules migrate` command will expose dry-run by default and use
the existing mutation admission, authorization, and expected-HEAD conventions
before apply. Ambiguous or unparsable input fails without rewriting the file.

Alternative considered: manually rewrite this repository and leave the
migration helper unreachable. Rejected because its existing next action would
continue directing adopters to a nonexistent and lossy command.

### 3. SQLite changes are versioned and data preserving

Schema version 2 will remove the retired empty `cache_entries` table through the
normal initializer. The migration will preserve event, chronicle, retrieval,
and lease tables and record version 2 only after the transaction succeeds. Both
state initialization paths will share one schema owner so a new database and an
upgraded database cannot diverge.

Alternative considered: delete and recreate `state.sqlite`. Rejected because
the database contains active Work Lane coordination that must survive cleanup.

### 4. Local-state maintenance is explicit, conservative, and deterministic

The existing local-state owner will gain an explicit maintenance mode; its
default audit mode remains read-only. Lease pruning removes only rows that are
expired and whose recorded branch, Git ref, linked worktree, and recorded path
are all absent. Unexpired, current, ambiguous, or still-observable leases remain.
Proof pruning removes records whose HEAD is unreachable from every current Git
ref while always retaining current HEAD; invalid records are reported rather
than silently discarded. The report lists every retained and removed identity
and is written under generated evidence, not tracked truth.

Alternative considered: automatic pruning during status or state reads.
Rejected because observation must not hide or mutate coordination history.

### 5. Recovery snapshots cross a preservation gate before deletion

The complete July 9 snapshot directory will be packed into an operator-selected
archive outside `.ethos/state/`. A manifest will bind every archived entry, the
archive SHA-256, byte size, bundle verification result, and operator archive
location. A tracked Chronicle receipt will bind the manifest digest and Git
HEAD. Only after archive extraction and bundle verification succeed may the
source snapshot directory be removed.

Alternative considered: retain only the three Git bundles. Rejected because
dirty patches and untracked-file snapshots can contain recovery material not
represented by bundle objects.

### 6. Expired source-budget debt closes by real net deletion

Each expired record will be mapped to its named replacement and measured
carrier categories. Redundant feature-local helpers, duplicated fixtures,
temporary adapters, and duplicated declarative wiring will be consolidated into
existing semantic owners. The record and wave are removed only after the live
inventory demonstrates that their allowance is no longer needed. The baseline,
terminal targets, unexpired records, and inventory categories remain unchanged.

Alternative considered: one new umbrella debt record. Rejected because it would
roll expired debt forward without delivering the promised compression.

### 7. Provider contracts remain; bundled reference executables retire

The provider-neutral external receipt and independent-verification contracts
remain product behavior. The two default-off Python reference executables under
`extensions/independent-verification/adapters/` will be removed from the product
repository and distribution surface because they are operator implementations,
not ETHOS ontology or required runtime. Documentation will retain the protocol,
installation boundary, and replacement guidance; focused contract tests move to
the canonical receipt/admission owners.

Alternative considered: move the same executables into `packages/`. Rejected
because that only reclassifies 504 lines and would incorrectly promote an
optional provider implementation into the product runtime.

## Risks / Trade-offs

- **[Risk] A rules rewrite truncates quality policy** -> migration tests compare
  parsed `[quality]` before and after and apply only after a dry-run target passes.
- **[Risk] Lease pruning removes recoverable coordination** -> require expiry and
  simultaneous absence of branch ref, worktree, and recorded path; report exact
  deleted lease IDs.
- **[Risk] Proof retention removes promotion evidence still in use** -> preserve
  current HEAD and every ref-reachable proof; land and publish consume current
  HEAD evidence only.
- **[Risk] Recovery archive is corrupt or workstation-specific** -> bind entry
  and archive digests, verify extraction, and run `git bundle verify` before
  deleting the source copy.
- **[Risk] Compression deletes semantic coverage** -> use red/green regression
  slices, preserve scenario matrices declaratively, and run the complete suite
  with 100% coverage before closing debt records.
- **[Trade-off] Conservative proof retention keeps reachable ancestor records**
  -> this avoids speculative loss now; later size caps require a separate policy
  change with explicit retention guarantees.

## Migration Plan

1. Commit the OpenSpec contract and focused failing tests.
2. Remove dead tracked projections and update adopter scaffold parity.
3. Make Rules V2 migration lossless, expose its guarded CLI, and migrate the
   product rules file without changing active quality, format, determinism, or
   artifact semantics.
4. Retire bundled independent-verification executables while preserving the
   provider-neutral receipt contract and its canonical admission tests.
5. Introduce SQLite schema version 2 and run it against a copied database before
   upgrading the Work Lane's ignored state in place.
6. Add and prove explicit local-state maintenance, then prune only eligible
   leases and proof records.
7. Create, hash, extract-test, and bundle-verify the recovery archive; write the
   Chronicle receipt; then remove the disposable source snapshots.
8. Complete measured carrier consolidation and remove only debt records whose
   allowance has been eliminated.
9. Run focused gates, full tests, parity, HEAD-bound executed proof, land, and
   local publication readiness. Remote push remains deferred.

Rollback uses Git revert for tracked changes. Before local-state mutation, copy
the SQLite database and proof/snapshot manifests into the operator archive. A
failed migration restores the copy; a failed preservation check leaves the
source snapshots untouched.

## Open Questions

None. The cleanup predicates, preservation boundary, and source-budget
constraints are fixed by the approved change.
