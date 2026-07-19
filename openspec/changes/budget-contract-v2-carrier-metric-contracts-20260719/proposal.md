# Budget Contract v2 Typed Carrier And Metric Contracts

## Why

The accepted Budget Contract v2 decision defines native metric domains, exact-one
carrier classification, deterministic contract identity, and non-compensating
coordinates, but the repository does not yet have typed v2 carrier and metric
contracts that later measurement adapters can consume. The current
`SourceBudgetTaxonomy` remains a v1 input and cannot be promoted implicitly into
v2 truth.

## What Changes

- Add an independent, versioned carrier manifest and strict typed models for
  carrier identity, exact-one classification, explicit reviewed exclusions, and
  fail-closed load results.
- Add a typed Git-present inventory envelope whose successful path set is
  non-empty, unique, stably ordered, and derived from one tagged Git observation.
- Reject Git command or OS failure, malformed inventory output, an empty
  inventory, unsupported tracked object modes, symlinks, gitlinks, and symlinked
  ancestors as explicit required gaps without exposing a clean partial result.
- Define an enumerated canonical segment matcher dialect: `*` matches one
  segment and `**` matches recursively. Reject the declared non-canonical syntax
  and redundancy set, including trailing `**/*`, adjacent `*`/`**` segments,
  repeated recursive segments, `?`, character classes, redundant
  root/recursive-basename pairs, redundant extension suffixes, and terminal
  suffix globs when `extensions` already owns the suffix.
- Add an independent, versioned metric registry for profiles and contracts that
  bind metric, parser, grammar, normalization, aggregation, and
  non-compensation identity.
- Compute manifest, inventory, and contract-set digests from canonical validated
  data. Public inventory construction revalidates canonical path/id/gap tokens,
  stable match order, exact gap aggregation, full match identity, and its
  supplied digest.
- Reject unknown fields, duplicate identities or matchers, invalid path rules,
  unsupported governed extensions, dangling profiles, BPE/model-token metrics,
  and compensating hard coordinates.
- Correct the implementation plan to name the carrier-manifest SSOT, typed Git
  inventory API, and symmetric metric load envelope.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `contracts`: subject=budget-contract-v2-carrier-metric-contracts;
  reuse=extend; change=modify;
  facet:lifecycle=authoring,validation,migration;
  facet:surface=contracts,schema,policy,adapter;
  facet:authority=source,test,schema,config,openspec,claim,evidence.

## Impact

This Change adds two contract modules, two policy manifests, two JSON Schemas,
one repository classification and inventory adapter, focused
contract/adapter/schema tests, the bounded claim and Chronicle, and the
corresponding contracts-spec delta. It does not change the authoritative v1
source-budget gate, baseline, allowance, debt, campaign, or required/advisory
semantics.

## Out Of Scope

- Lexical-token, semantic-node, normalized-byte, template, parser, or Git-blob
  measurement.
- Opening carrier bytes or claiming a race-free content snapshot. Task 3 must
  bind measurement-time reads through a no-follow or immutable-snapshot
  strategy.
- Snapshot replay, v2 shadow reporting, vector policy, Debt v2, changed-scope
  admission, dual control, DR-0009 calibration, cutover, or v1 global LOC
  retirement.
- Modification of `.ethos/rules.toml`, `system/commands.toml`, the current v1
  taxonomy, `source_budget_report` routing, or the v1 inventory adapter.
- Candidate land, accepted-root closeout, remote publication, hosted CI, or
  foreign Work Lane mutation before their separate native transitions.
