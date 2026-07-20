# Budget Contract v2 Content-Bound Native Measurement

## Why

Budget Contract v2 now has typed carrier and metric declarations, but it cannot
yet bind repository bytes to deterministic native measurements. Without a
content-bound adapter, statement packing, minification, giant literals, parser
failure, runtime-version drift, or a worktree object swap can still produce a
plausible but untrustworthy vector.

## What Changes

- Add strict frozen, self-verifying measurement contracts for native metric
  values, carrier observations, coordinate aggregation, snapshot identity, and
  symmetric fail-closed load envelopes.
- Add descriptor-relative, no-follow worktree reads that validate every path
  component, require a regular file, compare object state before and after the
  read, and reject any drift without returning a partial clean result.
- Add contract-driven native providers for UTF-8 footprint/control files,
  Python, TOML, JSON, YAML, INI, Jinja, the repository's Bash/Zsh-capable shell
  lexical subset, and the repository's C4 declaration grammar.
- Reconcile the later minimal-adoption change by restoring `template_source`
  and a product-owned Jinja carrier only for parse-only source-budget
  measurement; do not restore adoption scaffold templates or rendering.
- Repair that change's incomplete canonical promotion by adding `Minimal
  Adoption Binding`, removing the stale full-scaffold and overlay requirements,
  and replacing the five remaining stale adoption requirement bodies without
  rewriting historical evidence.
- Harden explicit adoption-root resolution so missing or non-directory targets
  reach the existing `git_repository_missing` verdict instead of failing before
  JSON admission output.
- Record one fresh digest-only, provider-neutral observation of the one-binding
  create and conflict paths at the implementation revision; do not relabel a
  synthetic adopter as native-backend parity.
- Extend the metric contract owner and generated JSON Schema with Jinja's three
  non-compensating coordinates: dynamic units, canonical dynamic payload bytes,
  and static data/comment bytes.
- Implement Shell v4 in the semantic `measurement/native/shell/` subpackage,
  including function headers, case phases, Zsh parameter forms, quote-removed
  heredoc words, line continuations, contextual nested substitution closers,
  recursion-exhaustion classification, and fail-closed no-progress guards.
- Make YAML 1.2 key uniqueness compare tag plus canonical scalar identity while
  preserving tag-distinct Python-equal keys in typed storage rather than a
  lossy Python dictionary.
- Replace ambiguous runtime labels with provider identities that bind the
  canonical CPython 3.14 measurement runtime, admitted dependency major,
  repository algorithm version, reproducible grammar descriptor, and runtime
  conformance fingerprint; correct the inaccurate POSIX-only shell identity.
- Bound PyYAML to its admitted major version and retain Jinja2 only as the
  measurement provider's admitted parser dependency alongside the candidate's
  native TOML serializer.
- Declare Jinja2's intentional lazy loading through one exact, package-scoped
  deptry rule in both the policy owner and runner; do not add a broad dependency
  exception or eagerly import the provider.
- Add an adversarial corpus encoded in one test-domain TOML carrier and tests
  for formatting games, identifier shortening, giant payloads, duplicate keys,
  non-finite structured and Jinja values, unsafe YAML graphs/tags, invalid UTF-8, BOM/CRLF,
  unavailable or mismatched providers, symlink/object swaps, reversed order,
  domain movement, digest forgery, and partial-result rejection.
- Map memory/resource exhaustion to stable non-sensitive gaps, close every
  opened descriptor on every exit path, and retain bounded execution or a
  versioned carrier-byte ceiling as a required pre-activation decision.
- Correct the implementation plan to use a module-layout-compliant semantic
  subpackage and fail-closed public interfaces.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `contracts`: subject=budget-contract-v2-native-measurement;
  reuse=extend; change=modify;
  facet:lifecycle=authoring,validation,migration;
  facet:surface=contracts,adapter,policy,evidence;
  facet:authority=source,test,config,openspec,claim,evidence.
- `repository-governance`: subject=minimal-adopter-binding-reconciliation;
  reuse=extend; change=modify;
  facet:lifecycle=adoption,validation;
  facet:surface=cli,contract;
  facet:authority=source,test,openspec.
- `quality`: subject=dynamic-parser-dependency-hygiene;
  reuse=extend; change=modify;
  facet:lifecycle=validation;
  facet:surface=config,script,test;
  facet:authority=source,test,config,openspec.

## Impact

This Change updates the carrier contract, carrier manifest, generated carrier
schema, metric contract owner, and generated metric schema; reconciles the
canonical budget design and global declarative-compression plans; and adds a
bounded repository measurement subpackage with a two-module Shell semantic
subpackage, focused kernel/adapter/regression tests, one TOML corpus, the bounded
claim and Chronicle, a contracts-spec delta, and a repository-governance delta
that repairs canonical minimal-adoption truth already implemented by source and
tests. It also updates the deptry policy, owner runner, architecture test, and
quality-spec delta for the exact lazy Jinja provider boundary. It updates provider semantic
versions, reviewed conformance constants, and grammar identities atomically,
narrows PyYAML to its admitted major, retains the candidate's native TOML
serializer, re-admits Jinja2 solely for parse-only measurement, and makes an
unusable explicit adoption root fail closed through the existing repository gap.
It adds a bounded one-binding external-adopter observation without native-backend,
semantic, hosted, remote, authority, or independent-review claims. It does not
restore the retired adoption renderer or change the package-wide Python minimum.
Native measurement succeeds only on the separately declared canonical runtime
and remains inactive in T3.

## Out Of Scope

- Git blob or HEAD object identity, immutable multi-file Git snapshots,
  historical replay, or v2 shadow reporting; those remain Task 4.
- Vector policy, Debt v2, changed-scope admission, command or gate activation,
  calibration, dual control, cutover, or v1 global LOC retirement.
- Modification of .ethos/rules.toml, system/commands.toml, system/gates.toml,
  v1 measurement, v1 baseline/debt, or current v1 report/gate routing.
- BPE/model-token metrics, parser-version inference, best-effort zero values,
  partial vectors, template rendering, or execution of measured source.
- Rewrite of the 2026-07-19 minimal-adoption archive, its historical claim or
  Chronicle, restoration of scaffold templates/rendering/overlay/profile
  variants/`init`, generated provider CI, or automatic adopter migration.
- Broad dependency-hygiene exemptions, eager parser imports, or suppression of
  unused-dependency findings for any package other than the exact Jinja provider.
- Admission of CPython 3.12 or 3.13 as successful measurement runtimes without a
  later provider contract and conformance fingerprint.
- Remote publication, hosted CI claims, foreign Work Lane mutation, or
  accepted-root writes before their separate lifecycle transitions.
