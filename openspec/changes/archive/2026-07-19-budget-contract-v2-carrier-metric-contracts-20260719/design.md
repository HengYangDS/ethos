## Context

DR-0008 and the approved Budget Contract v2 design require every maintained
carrier to be classified exactly once or explicitly excluded, and every hard
metric coordinate to bind a stable parser/grammar/normalization contract. The
current v1 format-selection taxonomy does not carry those semantics and remains
authoritative only for v1.

Task 2 is the contract boundary between the completed Foundation and Task 3
measurement. It must make invalid or ambiguous declarations impossible, provide
a typed Git-present inventory, and preserve a hard boundary before file-content
measurement or enforcement.

## Goals / Non-Goals

**Goals:**

- Establish separate carrier and metric policy SSOTs with strict frozen models.
- Return explicit fail-closed load envelopes for missing, malformed, invalid, or
  unavailable declarations and Git inventory.
- Make successful Git-present inventories non-empty, unique, stably ordered,
  partial-result-free, and bound to one tagged Git enumeration.
- Reject unsupported Git object modes and symlinked path components without
  following them as repository files.
- Make path classification pure, repository-relative, POSIX-based, exact-one,
  segment-aware, canonical, and deterministic.
- Make validated contract digests invariant to declaration order while changing
  for every semantic field; make `CarrierInventory` verify its own order, gaps,
  and digest.
- Give Task 3 a complete carrier inventory and resolvable metric profiles without
  allowing it to infer classifications or defaults.

**Non-Goals:**

- Read file contents, invoke a parser, count any metric, or produce a
  `CarrierMeasurement`.
- Guarantee that the worktree cannot mutate after inventory enumeration or
  between `lstat` and a future Task 3 byte read.
- Change v1 policy, adapter, baseline, debt, gate state, report state, or command
  routing.
- Calibrate limits or admit any v2 authority transition.

## Decisions

1. **Independent SSOTs.** `system/policies/source-budget-carriers.toml` owns v2
   carrier declarations and `system/policies/source-budget-metrics.toml` owns v2
   profiles and metric contracts. Neither loader reads
   `.config/checks/format/selection.toml`.
2. **Strict immutable contracts.** Public contract models are frozen Pydantic
   models with `extra = "forbid"`. Manifest, metric-registry, and Git-inventory
   load envelopes are frozen slotted dataclasses. A successful Git inventory
   requires non-empty, unique, stably ordered strings; a failed load requires
   `paths = None` and non-empty stable required gaps.
3. **Enumerated canonical segment matcher dialect.** Repository-relative
   POSIX matcher segments are literal, single-star, or recursive-double-star
   forms. `*` never crosses `/`; `**` is recursive. The contract rejects the
   declared non-canonical syntax and redundancy set: absolute paths,
   backslashes, `..`, empty segments, repeated recursive segments, adjacent
   whole-segment `*`/`**`, trailing `**/*`, `?`, character classes, redundant
   exact/`**/basename` pairs, suffix extensions that subsume one another, and
   terminal suffix globs when `extensions` is non-empty. It does not claim a
   general theorem over every possible glob or normalize arbitrary equivalence
   across otherwise distinct declaration fields.
4. **Exact-one classification and self-verifying inventory.** All matching rules
   are evaluated; no priority, specificity, or first-match rule resolves
   ambiguity. `CarrierMatch` carries an explicit `path_state = valid|invalid`,
   requires a canonical path for valid input or a digest-suffixed safe label for
   invalid input, and validates non-empty stable matched IDs and gap tokens.
   Synthetic status is never inferred from the pathname string. `CarrierInventory`
   requires unique stable `(relative_path, path_state)` keys, exact match-level
   gap aggregation, an explicit empty-inventory gap, and a digest recomputed from
   manifest digest, full match identity, paths, path states, classification
   states, IDs, and required gaps.
5. **One typed Git observation.** The adapter runs one strictly NUL-framed tagged
   `git ls-files --stage --cached --others --exclude-standard` observation.
   Tracked stage records and non-ignored untracked paths are parsed from the same
   command output, removing the prior two-command omission window. Missing final
   NUL, empty records, unknown tags, invalid tag/stage combinations, non-zero
   exit, any `OSError`, or an empty clean result fail closed. A regular tracked
   path that is unstaged-deleted is intentionally absent from the Git-present
   worktree inventory; unsupported modes remain blocking even when not
   materialized.
6. **No-follow object boundary.** Tracked modes other than regular-file
   `100644`/`100755` are rejected before worktree materialization is consulted,
   so symlinks and gitlinks cannot disappear when absent. Every ancestor and the
   final object are inspected with `lstat`; a symlink ancestor, final symlink,
   non-directory ancestor, unreadable object, or mode/object mismatch is a
   required gap and no partial path set is returned.
7. **Explicit classification failure states.** Classification returns
   `classified`, `excluded`, `unclassified`, `ambiguous`, or `unsupported` plus
   stable matched IDs and required gaps. A measured rule requires a metric
   profile; an exclusion requires owner and reason and cannot carry a metric
   profile.
8. **Versioned metric profiles.** A metric profile binds a carrier role to its
   required metric IDs. Each metric contract binds the DR-0008 identity fields,
   uses `aggregation = "sum"`, and requires `non_compensable = true`.
   Repository-source contracts reject model/BPE/tokenizer units and fields.
9. **Canonical digests.** Digests are SHA-256 over UTF-8 compact JSON from
   validated model dumps with sorted keys and stable identity ordering. Digests
   exclude themselves, timestamps, absolute roots, declaration order, traversal
   order, locale, and runtime state.
10. **T2/T3 boundary.** T2 classifies a static Git-present observation and checks
    current path components without opening carrier bytes. A later worktree
    mutation remains possible. Task 3 must measure through descriptor-relative
    no-follow opens or an immutable Git snapshot and must fail closed if the
    observation cannot be bound to the bytes measured.

## Public Interfaces

```python
def load_carrier_manifest(root: Path) -> CarrierManifestLoad: ...
def load_present_worktree_paths(root: Path) -> PresentWorktreePathsLoad: ...
def classify_carrier(
    relative: str,
    manifest: CarrierManifest,
) -> CarrierMatch: ...
def classify_carriers(
    paths: Iterable[str],
    manifest: CarrierManifest,
) -> CarrierInventory: ...
def load_metric_contracts(root: Path) -> MetricContractSetLoad: ...
def resolve_metric_contracts(
    identity: CarrierIdentity,
    contracts: MetricContractSet,
) -> tuple[MetricContract, ...]: ...
```

All three load envelopes carry either validated data or non-empty required gaps.
A missing or invalid declaration, unavailable Git command, malformed inventory,
or empty path set never produces an empty successful contract.

## Risks / Trade-offs

- [Broad globs overlap] -> validate every rule, restrict the matcher dialect, and
  run the current Git-present inventory through exact-one classification.
- [Known matcher aliases or redundancies change identity] -> reject the
  enumerated canonicality violations and state explicitly that arbitrary
  `fnmatch` equivalence outside that declared set is not inferred.
- [Git failure or malformed output becomes zero] -> return a typed failure
  envelope and forbid partial paths whenever any inventory gap exists.
- [Gitlink or symlink is not materialized] -> judge tracked object kind from Git
  mode before checking the worktree.
- [A symlinked ancestor redirects outside the root] -> `lstat` every ancestor
  without resolving or following it.
- [The worktree mutates after enumeration] -> do not claim race-free bytes in
  T2; Task 3 must bind the measured bytes using no-follow or snapshot semantics.
- [A new extension silently disappears] -> classify an unmatched unregistered
  suffix as `unsupported` and require a manifest update or reviewed exclusion.
- [A forged inventory reuses a plausible digest] -> recompute and verify the
  public inventory digest during model validation.
- [Task 3 re-infers policy] -> expose inventory, profile resolution, and digests
  as the only admitted measurement inputs.
- [Schema drifts from models] -> compare committed compact schemas with the
  model-generated projections in governance tests.

## Migration Plan

1. Add RED contract, adapter, schema-projection, Git failure, object-kind,
   symlink-ancestor, matcher-canonicality, and inventory-forgery tests.
2. Implement strict models, canonical digests, three fail-closed loaders, one
   tagged Git observation, no-follow path checks, and pure classification.
3. Add both declarative manifests and validate the current maintained inventory.
4. Prove the v1 adapter remains byte-for-byte unchanged.
5. Run focused tests, lint, schema/config checks, module-layout, source-budget,
   strict OpenSpec, claims, changed-scope planning, parity, independent review,
   and HEAD-bound proof.
6. Complete official archive inputs. Archive, archive-HEAD proof, candidate land,
   accepted-root closeout, local publication, and Lane retirement remain
   separately evidenced lifecycle transitions.

Rollback before land removes the T2 contracts and declarations while leaving the
v1 source-budget path unchanged. An archived carrier is never rewritten.

## Open Questions

None. Parser behavior, measurement corpora, content normalization, and
measurement-time no-follow/snapshot binding belong to Task 3.
