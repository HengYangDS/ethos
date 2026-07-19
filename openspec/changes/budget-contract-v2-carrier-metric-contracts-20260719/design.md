## Context

DR-0008 and the approved Budget Contract v2 design require every maintained
carrier to be classified exactly once or explicitly excluded, and every hard
metric coordinate to bind a stable parser/grammar/normalization contract. The
current v1 format-selection taxonomy does not carry those semantics and remains
authoritative only for v1.

Task 2 is the contract boundary between the completed Foundation and Task 3
measurement. It must make invalid or ambiguous declarations impossible without
prematurely importing parsers or changing enforcement.

## Goals / Non-Goals

**Goals:**

- Establish separate carrier and metric policy SSOTs with strict frozen models.
- Return explicit fail-closed load envelopes for missing, malformed, or invalid
  declarations.
- Make path classification pure, repository-relative, POSIX-based, exact-one,
  and deterministic.
- Make validated contract digests invariant to declaration order while changing
  for every semantic field.
- Give Task 3 a complete carrier inventory and resolvable metric profiles without
  allowing it to infer classifications or defaults.

**Non-Goals:**

- Read file contents, invoke a parser, count any metric, or produce a
  `CarrierMeasurement`.
- Change v1 policy, baseline, debt, gate state, report state, or command routing.
- Calibrate limits or admit any v2 authority transition.

## Decisions

1. **Independent SSOTs.** `system/policies/source-budget-carriers.toml` owns v2
   carrier declarations and `system/policies/source-budget-metrics.toml` owns v2
   profiles and metric contracts. Neither loader reads
   `.config/checks/format/selection.toml`.
2. **Strict immutable contracts.** Public contract models are frozen Pydantic
   models with `extra = "forbid"`. Load/result envelopes are frozen slotted
   dataclasses so invalid input cannot masquerade as an empty clean contract.
3. **Exact-one classification.** Rules use repository-relative POSIX paths,
   include globs, explicit excludes, and normalized lowercase dotted
   extensions. Absolute paths, backslashes, `..`, empty matchers, duplicate IDs,
   and duplicate matcher identities are rejected. All matching rules are
   evaluated; no priority, specificity, or first-match rule resolves ambiguity.
4. **Explicit failure states.** Classification returns `classified`,
   `excluded`, `unclassified`, `ambiguous`, or `unsupported` plus stable matched
   IDs and required gaps. A measured rule requires a metric profile; an
   exclusion requires owner and reason and cannot carry a metric profile.
5. **Versioned metric profiles.** A metric profile binds a carrier role to its
   required metric IDs. Each metric contract binds the DR-0008 identity fields,
   uses `aggregation = "sum"`, and requires `non_compensable = true`.
   Repository-source contracts reject model/BPE/tokenizer units and fields.
6. **Canonical digests.** Digests are SHA-256 over UTF-8 compact JSON from
   validated model dumps with sorted keys and stable identity ordering. Digests
   exclude themselves, timestamps, absolute roots, declaration order, traversal
   order, locale, and runtime state.
7. **T2/T3 boundary.** The repository adapter may enumerate and classify
   Git-present paths, but it does not open file contents or import parsers.
   Parser identifiers are inert contract data until Task 3 resolves them through
   owned adapters.

## Public Interfaces

```python
def load_carrier_manifest(root: Path) -> CarrierManifestLoad: ...
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

Both load envelopes carry either validated data or non-empty required gaps. A
missing or invalid file never produces an empty successful manifest or registry.

## Risks / Trade-offs

- [Broad globs overlap] -> validate every rule and run current Git-present
  inventory through exact-one classification; ambiguity is blocking.
- [A new extension silently disappears] -> classify an unmatched unregistered
  suffix as `unsupported` and require a manifest update or reviewed exclusion.
- [Contract order changes digests] -> sort semantic collections by stable
  identities before canonical serialization.
- [Task 3 re-infers policy] -> expose inventory, profile resolution, and digests
  as the only admitted measurement inputs.
- [Schema drifts from models] -> compare committed compact schemas with the
  model-generated projections in governance tests.

## Migration Plan

1. Add RED contract, adapter, and schema-projection tests.
2. Implement strict models, canonical digests, loaders, and pure classification.
3. Add both declarative manifests and validate the current maintained inventory.
4. Run focused tests, lint, schema/config checks, strict OpenSpec, claims,
   changed-scope planning, parity, and HEAD-bound proof.
5. Archive this Change, regenerate archive parity and archive-HEAD proof, then
   perform candidate/accepted/local-publication transitions separately.

Rollback before land removes the T2 contracts and declarations while leaving the
v1 source-budget path unchanged. An archived carrier is never rewritten.

## Open Questions

None. Parser behavior, measurement corpora, and content normalization belong to
Task 3 and remain outside this Change.
