## Why

ETHOS currently carries multiple parallel semantic owners, private runtimes,
self-scoring views, oversized outputs, provider-specific coupling, and tests that
preserve implementation branches rather than product behavior. This makes a
simple intent-to-repository transition slow, expensive, difficult to recover,
and capable of reporting green while a hard source-budget gap remains.

One destructive campaign is required now because incremental compatibility work
has repeatedly increased surface area without reaching the declared terminal
budgets or the vendor-neutral product boundary.

## What Changes

- **BREAKING** Replace the current product ontology with `ChangeContract` and
  `Attestation`, plus derived `RepositoryFacts` and transient `PlanIR`.
- **BREAKING** Fold `orient` into `status`, remove `report`, and use only
  `pass | block | unknown` with hard gaps never coexisting with a green state.
- **BREAKING** Delete the private source-budget worker/protocol/replay/shadow
  stack and retain one direct deterministic measurement path.
- **BREAKING** Remove all workstation-specific control-plane code, schema, test,
  documentation, and evidence coupling; ETHOS remains independently installable
  and operable.
- **BREAKING** Replace `proposal/*` with provider-neutral `proposal/*`; keep
  `candidate/dev` and `work/*` local-only and publish only `main`, `dev`, and
  `proposal/*`.
- Replace custom graph layers with direct `graphlib.TopologicalSorter` and cut
  the single guard DSL to official CEL after parity.
- Introduce Worktree Family semantics, cooperative and competitive strategies,
  intent amendments, vendor-neutral handoff/takeover, adaptive backpressure,
  and a serialized candidate CAS update point.
- Make Cyclopts declarations the CLI source of truth and bound default command
  payloads to compact summaries plus artifact references.
- Establish one owner per format, lint, type, test, structural, supply-chain,
  provenance, version, and source-measurement property; warnings and production
  suppressions become hard failures.
- Prove kernel/adopter homomorphism with Python, Node/polyglot, and docs/infra
  repositories before exposing the minimal protocol and pack ecosystem.
- Run local closeout for campaign iterations and exactly one dual-provider
  remote closeout at the terminal commit.

## Capabilities

### New Capabilities

None. The campaign replaces and compacts existing product capabilities rather
than creating a parallel capability registry.

### Modified Capabilities

- `kernel`: subject=terminal-semantic-kernel; reuse=extend; change=modify
- `command-plane`: subject=terminal-command-plane; reuse=extend; change=modify
- `contracts`: subject=terminal-contracts; reuse=extend; change=modify
- `repository-governance`: subject=terminal-repository-governance; reuse=extend; change=modify
- `quality`: subject=terminal-quality-floor; reuse=extend; change=modify
- `adapters`: subject=terminal-adapter-boundary; reuse=extend; change=modify
- `distribution`: subject=terminal-distribution-topology; reuse=extend; change=modify
- `proof-hosts`: subject=terminal-conformance-proof; reuse=extend; change=modify
- `assistant-projections`: subject=terminal-agent-projections; reuse=extend; change=modify

## Impact

The campaign may replace any active package, schema, CLI, test, tool, CI,
document, OpenSpec, evidence, or local lifecycle implementation that conflicts
with the canonical terminal design. It intentionally provides no compatibility
shim. Intermediate code growth is allowed, but terminal Python ELOC is at most
54,000 and global owned-source ELOC is at most 68,000. Local operation remains
remote-independent; GitLab and GitHub are separately verified publication
planes. Foreign Work Lanes remain read-only unless their holders hand them off
or an explicitly authorized Lease takeover succeeds against fresh exact facts.


## Out of Scope

- Historical compatibility aliases, import shims, re-exports, redirects, dual runtimes, or old command and schema preservation.
- Mutation, landing, retirement, cleanup, or ownership takeover of foreign Work
  Lanes without holder handoff or exact authorized Lease takeover.
- A claim that the terminal implementation, terminal ELOC, provider CI/CD, protected branch advancement, release, or campaign closeout is already complete.
- A mandatory central marketplace, hosted workflow runtime, DI container, event bus, policy server, graph database, or workstation-specific control plane.
