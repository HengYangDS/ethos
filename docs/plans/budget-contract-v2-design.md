---
subject: ethos:quality:budget-contract-v2-design
role: plan
state: planned
relations:
  decided_by: docs/decisions/accepted/DR-0008-metric-domain-budget-contract.md
  governed_by: openspec/changes/archive/2026-07-19-budget-contract-v2-foundation-integration-continuation
---

# Budget Contract v2 Design

Status: approved for governed implementation on 2026-07-19; the Foundation carrier and its integration continuation were archived on 2026-07-19.

Purpose: replace the repository-wide use of effective lines of code as a
cross-language budget currency with a versioned, metric-domain vector while
retaining ELOC as a per-file readability ceiling.

See also: [Product Design Contract](../governance/product-design-contract.md),
[Global Declarative Compression Program](global-declarative-compression-program.md),
and [Decision Records](../decisions/README.md).

## Problem

The v1 source budget treats effective lines as one repository-wide currency.
That signal is useful for local reading span, but it is not invariant under
minification, semicolon packing, large literals, generated payloads, or movement
between code and declarative carriers. Characters detect payload growth but do
not express structure. Model-specific BPE tokens are operationally useful but
change with tokenizer and model choice and therefore cannot define repository
source truth.

The predecessor foundation observation was blocked with 17 required gaps. The
successor candidate base later projects campaign-terminal growth as advisory,
with terminal and debt facts still visible. Migration must preserve both facts:
it cannot reset the baseline, extend debt, raise the allowance, average-convert
LOC into another unit, or treat a projection change as settlement.

## Decision

Budget Contract v2 is a non-compensating vector, not a replacement scalar.
Every hard coordinate must pass independently.

| Domain | Primary hard measures | Boundary |
| --- | --- | --- |
| Authored programming source | language-native lexical tokens; normalized syntax/payload bytes | Repository source truth |
| Authored declarations | semantic nodes; normalized scalar payload bytes | Repository source truth |
| Templates | dynamic lexical/semantic structure; static payload bytes | Repository source truth |
| Individual source files | effective code lines | Readability/maintainability ceiling only |
| Tests | the same native measures, in a separate test scope | Cannot offset product source |
| Evidence and derived projections | separate footprint contracts | Cannot offset source or tests |
| Agent prompts and runtime context | model/tokenizer-specific BPE tokens | Operational budget only; never repository-source currency |

AST and CST objects are adapter mechanisms and diagnostics. They are not a
cross-language currency. A parser, grammar, lexer, normalization algorithm, or
aggregation rule is part of the metric contract and therefore versioned and
digested.

## Carrier Inventory

Every maintained repository byte is classified exactly once by a typed carrier
manifest or is excluded by an explicit, reviewed rule. Initial roles are:

```text
authored_behavioral_source
authored_declarative_source
template_source
test_source
derived_projection
evidence_instance
governance_history
documentation
vendor_or_lock
runtime_local
```

Zero matches, multiple matches, unsupported governed extensions, parser
unavailability, parse failure, invalid UTF-8, or a grammar/version mismatch are
required gaps. A source file moved into evidence or a generated path changes
domain; it does not disappear from governance.

The `SourceBudgetTaxonomy` already present on the successor candidate is the
current v1 carrier-classification input used by the ownership extraction. It is
not the future Budget Contract v2 carrier and metric contract, and its presence
does not claim Task 2 or v2 migration completion.

## Metric Contract

Each metric declaration binds at least:

```text
contract_id
contract_version
metric_id
unit
carrier_role
metric_profile
parser_id
parser_version
grammar_digest
normalization_id
normalization_version
aggregation
non_compensable
```

The observation for a carrier also binds its repository-relative path, tracked
identity, HEAD blob OID when available, content SHA-256, carrier rule, metric
contract digest, and adapter result. Snapshots are deterministic under file
order, locale, timezone, newline convention, and concurrency.

## Policy And Debt

Policy coordinates are `(scope_id, metric_id)`. The repository policy records
an immutable baseline vector, terminal vector, permanent allocations, settled
reductions, and temporary debt. Logical AND combines coordinates; bytes do not
compensate tokens, tests do not compensate product source, and one language does
not compensate another.

Debt v2 records the originating Change and admitted HEAD, scope and inventory
digests, per-coordinate allowances, per-coordinate expected deletion, owner,
expiry, deletion wave, and replacement. Every v1 debt item is remeasured from
its actual historical scope or remains explicitly `unmapped` and blocking.
Expired v1 debt stays expired. The original baseline remains
`2dab77f169eceb2d45f917358c2a7487e7ac8db6`.

## Change Admission And Global Closeout

Default proof gains a changed-scope `source-admission` gate. It compares the
current Work Lane with its candidate merge base and allows positive coordinates
only when the selected OpenSpec Change owns a matching allocation or temporary
debt record. Inherited global debt does not block a zero-increase or reducing
Change.

The repository-wide `source-budget` gate remains full-proof and terminal
compression evidence. Migration completion and compression completion are two
different claims:

- Migration completion means v2 is authoritative, v1 global LOC is retired, and
  per-file ELOC remains.
- Compression completion additionally requires every terminal coordinate to
  pass and active, expired, unmapped, and unclassified debt counts to be zero.

## Migration State Machine

```text
v1_authoritative_v2_shadow
-> v1_and_v2
-> v2_authoritative_v1_rollback
-> v2_authoritative
```

Shadow output always reports v1, v2, disagreement classification, metric and
carrier digests, baseline replay, parser coverage, unclassified carriers, and
adapter failures. The dual-control interval spans at least two complete local
candidate integration cycles with an unchanged metric contract. Parser or
grammar semantic changes reset that interval.

Cutover is blocked if any old required gap lacks either settlement evidence or
an equal-or-stronger named v2 successor gap. The preferred cutover condition is
both transition policies clean. An exception requires accepted DR-0009 to map
every remaining v1 obligation and v2 must remain visibly blocked.

## Historical Replay

Historical replay is gated by a versioned provider execution boundary. The
first bounded-only design was rejected on July 21, 2026 after an INI carrier of
9,590 bytes produced a 77.4 MiB Python peak, a 20,489,335-byte canonical stream,
and 2.87 seconds of work. Metric registry and atoms therefore advance to v4
and bind a static hybrid execution contract. The discarded reader/native GREEN
was never committed; the v3 metric-contract and diagnostic-test commits already
on the Work Lane remain migration input and must be superseded atomically.

Parser ids `utf8-footprint`, `utf8-control`, and `diagram-contract` are the only
providers admitted to `bounded_in_process_v1` under
`ethos-source-budget-execution:bounded-in-process-v1`. Parser ids
`python-tokenize`, `json-stdlib`, `tomllib`, `pyyaml-safe`, `configparser`,
`jinja2`, and `shell-lexical` use one-carrier/one-process `isolated_worker_v1`
under `ethos-source-budget-execution:isolated-worker-v1`, with no in-process
fallback. Both modes resolve the complete descriptor before content open,
perform one parent `limit + 1` read, and recheck direct bytes before parse or
spawn. Every atom binds the exact `(mode, ceiling, execution-contract id,
execution-contract digest)` tuple; the provider descriptor, not a path or
caller, selects it. The execution digest excludes parser/grammar/normalization
and coordinates, which provider descriptor v2 binds separately.

Worker protocol v1 is path blind, canonical, typed, length framed, and bounded.
Parent and child both revalidate content, contracts, provider identity,
execution identity, and ceilings. The supervisor enforces CPU, wall, memory
intent, descriptor/process, request/response, protocol, and output bounds, then
terminates and reaps the whole process group on failure. Linux and Darwin use
platform-specific enforcement while making the same resource-fault-isolation
claim. Darwin samples RSS every 10 ms and trips virtual-memory growth above the
first successful pre-request `pti_virtual_size` baseline plus 512 MiB; it is not
described as a kernel-hard absolute RSS/AS sandbox.

The carrier ceilings remain 262,144 bytes for `utf8-footprint`, 65,536 for
Python, and 32,768 for every other provider. They are execution boundaries, not
source-budget allowances, and cannot rise from current maxima. Static hybrid
routing reduces the planned replay workload from 2,889 worker starts to 873, a
69.8 percent reduction, without leaving any complex parser on the bounded path.
Cold-start seconds remain platform evidence to remeasure, not a design constant.

Baseline and selected historical snapshots are recomputed from Git blobs rather
than trusting declared totals. The observed v1 replay mismatch is itself a
migration fact: the declared v1 baseline total is 105342 while the current v1
algorithm replays 105060, a net drift of -282 ELOC. The replay deltas are
JavaScript 89 -> 90 (+1), YAML 1082 -> 800 (-282), and diagram 24 -> 23 (-1).
The governed inventory contains 933 files and has SHA-256
`f8e85ace7648b60592fbe6e678f78169afa98c6289b0e8bb7d7fbc3961fa1c8d`.
This correction supersedes the archived Foundation statement without rewriting
that historical archive. v2 must version the semantic drift; it must not
rewrite the declared v1 baseline.

## Evidence Boundary

Raw per-file observations, backtests, performance results, and shadow comparisons
live in ignored `build/evidence/`. Tracked claims and Chronicles contain reviewed
summaries and digests. Dry-run readiness is not executed proof, local proof is
not hosted proof, local publication readiness is not remote publication, and a
unit migration is not compression settlement.

## Rollback

Before cutover, v1 remains authoritative and v2 can be disabled without changing
v1 policy. During dual control, rollback returns enforcement to v1 and preserves
v2 evidence as experiment history. The v2 cutover and v1 retirement commits are
reverted together. An archived governance decision is never rewritten; rollback
uses a new OpenSpec Change and superseding decision record.

## Acceptance

The design is complete only when all of the following hold:

1. Every maintained carrier is classified exactly once.
2. Metric and grammar contracts are versioned and deterministic.
3. Baseline replay and every replay mismatch are explicit.
4. Every v1 debt item is settled or mapped without conversion.
5. Changed-scope admission is in default proof.
6. Repository-wide v2 remains in full proof and terminal closeout.
7. Dual control passes the declared observation interval.
8. DR-0009 accepts calibrated limits and cutover/rollback conditions.
9. v2 becomes authoritative and global v1 LOC is removed without removing
   per-file ELOC.
10. Terminal compression is claimed only after all terminal vectors and debt
    inventories are clean.
