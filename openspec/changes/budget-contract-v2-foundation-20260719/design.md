## Context

The v1 source budget aggregates effective lines across programming languages,
declarations, schemas, templates, tests, and derived carriers. Historical study
shows that line count can fall while characters, lexical tokens, or semantic
nodes grow. The current v1 report is already blocked and its declared baseline
also replays 283 ELOC lower under today's v1 algorithm because metric semantics
changed after the baseline commit.

## Goals / Non-Goals

**Goals:**

- Establish metric-domain boundaries before changing enforcement.
- Keep every v1 obligation visible and immutable during migration.
- Move existing v1 behavior into a focused domain owner without compatibility
  forwarding or semantic change.
- Define independently reviewable successor Changes through cutover and terminal
  settlement.

**Non-Goals:**

- No baseline reset, LOC-to-token conversion, allowance increase, expiry
  extension, terminal-target change, inventory exclusion, or proof-scope change.
- No v2 threshold calibration, authoritative cutover, global LOC retirement, or
  compression-complete claim in this Change.
- No LLM/BPE token budget in repository-source policy.

## Decisions

1. Repository-source budgets are non-compensating vectors. Programming source
   uses language-native lexical tokens and normalized syntax/payload bytes;
   declarations use semantic nodes and scalar payload bytes; templates separate
   dynamic structure from static payload. Tests, evidence, derived projections,
   and source remain separate scopes.
2. ELOC remains a per-file readability ceiling. It ceases to be a cross-language
   repository currency only after a later accepted cutover decision.
3. Parser, grammar, lexer, normalization, aggregation, and carrier classification
   are versioned contract inputs. Unsupported, unavailable, ambiguous, or invalid
   measurement fails closed.
4. The immutable v1 baseline remains
   `2dab77f169eceb2d45f917358c2a7487e7ac8db6`. Historical replay mismatch is
   evidence of metric drift, not permission to rewrite the declaration.
5. The first implementation step is behavior-preserving extraction to
   `ethos.domain.source_budget.core`. `ethos.domain.prove` keeps only its own
   code-size and validation responsibilities and exposes no compatibility
   forwarder.
6. Later Changes implement carrier/metric contracts, native measurement,
   historical replay, Debt v2, changed-scope admission, two-cycle dual control,
   DR-0009 calibration, v2 cutover, global LOC retirement, and terminal debt
   settlement.

## Risks / Trade-offs

- Vector measures are more complex than one scalar. Strict versioning,
  deterministic snapshots, and small pure reducers contain that complexity.
- Migration code temporarily increases source footprint. Each successor Change
  must pair growth with named deletion or preserve an explicit visible gap; the
  v1 allowance is not raised.
- Existing v1 metric drift prevents an "exact replay" claim. The migration
  records both the declaration and replayed observation and blocks silent
  normalization.

## Rollback

Before cutover, disable or revert v2 shadow components and keep v1 authoritative.
After archive, use a new OpenSpec Change and superseding decision rather than
rewriting history. The later cutover and v1-retirement commits must be reverted
as one unit.

## Proof

This Change requires focused extraction regressions, strict OpenSpec lifecycle,
claim digest validation, config and Python lint, parity refresh when stale, and
HEAD-bound executed default proof. The standalone v1 source-budget command is
expected to remain blocked with the same inherited obligations; that result is
preserved evidence, not a failure of behavior equivalence.
