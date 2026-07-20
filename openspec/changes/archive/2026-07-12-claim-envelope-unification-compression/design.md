## Context

The repository already defines the canonical trust-bearing envelope with
`[claim]`, `[evidence]`, `[boundary]`, `[carriers]`, and `[promotion]`.
However, fourteen tracked historical records use a second top-level format
(`id`, `lifecycle`, `evidence_refs`, and `promotion_targets`). The claim report
contains a dedicated branch and a separate output projection for that legacy
shape. This is procedural compatibility debt: it makes the source of claim
truth ambiguous and keeps tests that defend an obsolete representation.

The surrounding product is declaration-first: TOML holds durable facts; Python
loads files, verifies hashes and paths, and reduces facts into a read model.
The existing `EvidenceClaim` Pydantic contract remains the typed validation
boundary for active assurance bindings. This change removes a representation;
it does not introduce a second claim model, a migration runtime, or a new
framework.

## Goals / Non-Goals

**Goals:**

- Make every tracked claim use the one canonical envelope.
- Preserve historical evidence as historical: old heads are not reinterpreted
  as currentness claims.
- Keep all evidence digests, OpenSpec carriers, test references, and promotion
  targets explicit after migration.
- Delete legacy parsing, legacy record projection, and the associated tests.
- Make malformed top-level claim files fail closed with a deterministic gap.

**Non-Goals:**

- Rewriting already-canonical claims merely for stylistic normalization.
- Reclassifying historical claims as current or proving their old source heads.
- Changing the public command plane, hosted publication state, or evidence
  authority order.
- Adding a workflow, policy, DI, or effect framework.

## Decisions

1. **One persisted envelope, no runtime upgrader.** Each of the fourteen
   records is converted in source control before the reader changes. The
   runtime only accepts the canonical envelope. This gives one authority path
   and a visible Git migration rather than a hidden conversion layer.

2. **Historical freshness for inherited evidence.** Converted records use
   `mode = "historical"`: their dated evidence hashes are checked, but their
   archived heads do not claim current repository state. This preserves the
   old evidence boundary without minting an invalid HEAD assertion.

3. **Explicit evidence binding from prior test references.** Former
   `claim_bindings` remain explicit in `evidence.tests`. Active claims also
   retain `evidence_ids`, `binding`, and `verifier`, because those are their
   trust-bearing admission fields. Thus no test reference is silently
   discarded when the format is consolidated.

4. **Fail closed on a missing envelope.** The report emits
   `<file-stem>:claim_envelope_missing` and continues scanning remaining files.
   It does not guess whether an arbitrary TOML document is an old claim.

5. **No new abstraction beyond the existing typed evidence contract.** The
   migration reduces formats and code. The current frozen/validated
   `EvidenceClaim` remains the assurance boundary; adding another parallel
   envelope hierarchy would increase the exact surface being removed.

## Risks / Trade-offs

- **Migration metadata is incomplete** → derive each digest from the dated
  evidence file and check all converted records with the normal claims gate.
- **A historical record is accidentally made current** → use only historical
  freshness and assert no `head` or semantic digest is present.
- **Output consumers relied on legacy fields** → focused report tests assert
  the canonical projection and a fixture proves legacy input now fails closed.
- **A source deletion masks behavior loss** → run claims, evidence freshness,
  repository audit, schema/OpenSpec validation, changed-scope quality, and
  HEAD-bound proof before promotion.

## Migration Plan

1. Create the bounded OpenSpec carrier and migration claim.
2. Convert all tracked legacy claim files using their existing evidence and
   promotion facts; compute digest values from the tracked chronicles.
3. Delete the legacy parser/projection path and replace its tests with
   canonical-envelope and fail-closed coverage.
4. Validate every claim, archive the OpenSpec carrier, record evidence, prove,
   land, and close out through the governed lifecycle.

Rollback is a normal Git revert of this atomic migration. There is no persistent
runtime migration state to clean up.

## Open Questions

None. The scope is intentionally limited to the known tracked legacy shape.
