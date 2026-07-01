---
subject: ethos:product-design-contract
role: decision
state: canonical
relations:
  canonical_for: product truth, migration boundary, and repository governance design
---

# Product Design Contract

ETHOS means Evidence-grounded Trust for Human-Agent Operational Stewardship.
ETHOS is the evidence-grounded operating layer for human-agent repository
change.

The product answers five transition questions and two read-only questions:

```text
Where am I?
Can I mutate?
How should I change this repository?
Which gates are required?
Is the evidence sufficient?
Can this land?
Can this publish?
```

The public command plane is:

```bash
ethos status
ethos plan
ethos prove
ethos land
ethos publish
```

`ethos report` is a read-only scorecard. It is a payoff view over readiness,
proof, parity, and release policy; it is not a sixth transition verb.

Setup and onboarding commands are outside the transition loop:

```bash
ethos init
ethos adopt
ethos doctor
```

Advanced workflows stay under `ethos ...` as maintainer/reference surfaces:

```bash
ethos campaign
ethos intake
ethos quality
ethos assistants
ethos playbooks
ethos fleet
ethos lane
ethos parity
ethos explain
ethos docs
```

## Kernel Chain

ETHOS is kernel-first. The product model is:

```text
JudgmentSource -> Subject -> Commitment -> Change -> Evidence -> Claim -> Chronicle
```

- JudgmentSource: authority order, truth boundaries, product principles, and
  decision policy. North Star is a derived reader view, not the judgment source.
- Subject: the governed object, such as a path, package, domain, surface,
  evidence set, or release target.
- Commitment: the Subject's contracts, policies, specs, rules, promises, and
  durable decisions.
- Change: the lifecycle owner for planned, active, landed, superseded, or
  retired repository truth. Contract, IR, Transition, and Inscription are fields
  or phases inside Commitment and Change, not competing top-level owners.
- Evidence: gate runs, digests, HEAD binding, CI proof, attestations, and
  artifacts.
- Claim: digest-bound or verifier-bound evidence binding.
  Claim binds evidence; it does not own the Change lifecycle.
  It must not assert semantic truth unless a semantic verifier actually checked
  that truth.
- Chronicle: judged execution and history index: what happened, which evidence
  was used, which decision was made, what was superseded, and how current truth
  changed.

## Governed Repository

ETHOS uses one governed repository model. The governed subject is always a Git
repository. Product repositories, adopted repositories, and reference
repositories differ by profile, capability set, and proof depth; they are not
separate ontology roles and do not create separate command planes.

The ETHOS product repository is governed with the `product` profile. Other
repositories are governed with their selected adoption or domain profile. The
profile changes required checks, adapters, and proof depth; it does not change
the subject kind or the command semantics.

Command payloads that audit or summarize repository governance expose
`governance_context`. That context records the profile, repository subject,
single-kernel flag, kernel chain, shared transition commands, scorecard
commands, repository truth boundary, and profile or adapter boundary.
The shared transition semantics are exposed as `shared_commands` and
`transition_commands`: `ethos status`, `ethos plan`, `ethos prove`,
`ethos land`, and `ethos publish`. Read-only scorecard semantics are exposed as
`scorecard_commands`: `ethos report`. `ethos audit --mode shape` and
`ethos audit --mode deep` select proof depth for the same governed repository
contract.

## Principles

### Judgment-source first

Product decisions cite the Judgment Source, user instruction, repository truth,
or accepted decisions. Reader-facing North Star language is derived from that
source and cannot override it.

### Kernel-first

Folders and packages follow the kernel chain. Package names do not create
separate truth centers.

### Contracts before providers

Provider-neutral contracts precede hosted forge, runtime, model, editor, and
toolchain implementations. OpenSpec is the current mandatory official
governance dependency for promoted spec records and deep proof. Backlog, MCP,
ACP, Superpowers, GitHub, GitLab, Dagger, Pants, SLSA, pytest, Ruff, pixi, and
similar systems are adapters, providers, profiles, method packs, or
product-toolchain tools; they are not ontology anchors.
OpenSpec remains mandatory governance, not a product substrate and not a
second command plane.

### Git-native repository substrate

ETHOS is Git-native. Commits, refs, branches, worktrees, HEAD binding, and
configured branch roles are product semantics, not a generic VCS abstraction.
Hosted forges, review systems, and CI surfaces may project those Git facts, but
they do not replace them.
Configured branch roles are reported through `role_policy` and ordered as
release_root -> accepted_root -> candidate -> work_lane -> submit_lane. The
branch names and prefixes are configurable, but the roles are product semantics.
The configured role policy is auditable through its configuration source,
configuration keys, default-policy state, semantic role order, and configured
patterns; release_root and accepted_root are both protected roles but they are
not interchangeable.
Work Lane lifecycle commands are also product semantics: `ethos lane start`,
`ethos lane bind-claim`, `ethos land`, and `ethos lane retire-landed` define the
local ownership, evidence binding, candidate closeout, and retirement path.
Git worktree facts remain observable, but raw worktree creation is not the
standard ETHOS lifecycle state because it bypasses ETHOS lease and claim
boundaries.

### Binding taxonomy

ETHOS distinguishes product-semantic hard bindings, mandatory governance
dependencies, native protocol bindings, product toolchain bindings, and
profile or adapter bindings. Git belongs to product semantics. OpenSpec belongs
to mandatory governance. JSON Schema, command JSON, TOML, JSONL, and ignored
SQLite local state are native protocols. The current Python, uv, Hatchling,
pytest, Ruff, and build workflow proves ETHOS itself but is not adopter ontology.
`ethos quality coupling-audit --json` exposes these classifications as a
`binding_registry` so product hard bindings, mandatory dependencies, native
protocols, product-toolchain tools, adapters, historical evidence, and fixtures are
auditable without binding ETHOS to a specific host or model provider.

### Capability before surface

Repository operation capabilities are defined before CLI, MCP, npm, CI, Docker,
Homebrew, GitHub Action, or GitLab Component surfaces. The CLI is public UX, not
the semantic center.

### Governance before tooling

ETHOS decides why a gate runs, which evidence is sufficient, whether a result is
trusted, and whether land or publish is allowed. Tools only observe, execute, or
translate.

### Proof separation

Conformance, parity, golden output, migration replay, and sample repositories
belong in an explicit proof host. They must not be scattered through runtime
packages as accidental product behavior.

## Truth Boundaries

Repository truth includes source code, tests, schemas, current docs, OpenSpec
records after promotion, claims, and durable evidence. Repo-authored projections
such as skills, assistant files, MCP descriptors, ACP descriptors, hosted CI
templates, and npm launchers are not truth by themselves.

Superpowers is an external method pack. Assistant host memory, fast mode, goals,
subagents, and doctor signals are host-local or session capabilities. MCP, ACP,
editor host surfaces, and assistant context bundles are context providers or
runtime projections. Agent output is never repository truth until promoted into
tracked artifacts and evidence.

## Trust Lifecycle

The trust-bearing repository lifecycle is:

```text
Claim -> Boundary -> Carrier -> Evidence -> Decision -> Promotion
```

An active claim needs an owner and scope boundary, an OpenSpec carrier, dated
evidence with a matching digest, fallback and kill-signal text, and promotion
targets. OpenSpec remains the official specification carrier, but a valid
OpenSpec change is not trusted without a bound claim and promotion evidence.
Work Lanes prove local ownership and write admission. Intake providers report
projection evidence. Neither Work Lane presence nor intake completion promotes
truth by itself.

Promotion targets are provider-neutral repository paths: source, tests, docs,
schemas, canonical OpenSpec specs, or dated evidence. Dry-run proof is readiness
only. Executed proof can support promotion when selected gates record passing
exit codes and the evidence is bound to a claim.

## Build And Release Contract

The current build contract is:

```text
uv workspace = dev, lock, run, and test orchestration
Hatchling = canonical PEP 517 build backend for Python packages
wheel/sdist = local smoke artifacts
PyPI/TestPyPI = future Python release channel, not current scope
npm = future thin launcher only, not a second implementation
Homebrew/Docker/CI = future distribution or runner adapters, not current scope
```

The current phase explicitly does not perform PyPI/TestPyPI publish, npm
registry publish, Homebrew publish, Docker/OCI push, GitHub Action marketplace
publish, or GitLab Component publish.

Status: see front matter.

Purpose: explain the repository truth represented by this ETHOS document.

See also: [Documentation Index](../index.md), [Command Plane](../reference/command-plane.md), and [Glossary](../reference/glossary.md).
