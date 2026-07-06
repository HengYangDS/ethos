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

## Root Philosophy

ETHOS keeps this root text:

# 问道

> 道隐无名，几动于微，法乎自然；
> 生一启元，分二判势，孕三冲和；
> 万象昭幽，度协畛域，枢得环中；
> 物遂其性，化育无穷，是谓玄德。

This is not an external slogan and not a feature map. It is the product's root
constraint: authority must stay deeper than named surfaces, small repository
signals must become visible before they become disorder, measures must fit their
boundaries, and governance must let Git, OpenSpec, evidence, claims, adapters,
local state, and assistant projections keep their own nature instead of being
absorbed into a false center.

Do not turn this root text into a line-by-line module map. Its engineering
reading is deliberately plain: JudgmentSource preserves authority; one single kernel keeps the center; truth boundary and profile or adapter boundary prevent
false absorption; binding taxonomy keeps measures domain-appropriate; command
JSON and evidence make hidden state inspectable; adapters remain adapters.
`system/tao.md` may restate these axioms for machine-adjacent review, but it is
not a separate product truth center and must stay derivable from this contract
and the kernel model.

Engineering names remain plain and precise: kernel, evidence, claim, chronicle,
adapter, profile, and transition loop mean what they say.

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
### Creative change with net gain

ETHOS does not preserve inherited shape for its own sake. Creative, destructive,
or simplifying changes are admissible when they produce provable net gain:
clearer authority, fewer entities, smaller surface area, stronger evidence,
better rollback, lower coordination risk, or removal of stale projections. A
disruptive change must declare what it deletes, what invariant it strengthens,
which evidence proves the gain, and how the repository can recover if the claim
fails.


### Contracts before providers

Provider-neutral contracts precede hosted forge, runtime, model, editor, and
toolchain implementations. OpenSpec is the current mandatory official
governance dependency for promoted spec records and deep proof. Backlog, MCP,
ACP, Superpowers, GitHub, GitLab, Dagger, Pants, SLSA, pytest, Ruff, pixi, and
similar systems are adapters, providers, profiles, method packs, or
product-toolchain tools; they are not ontology anchors.
OpenSpec remains mandatory governance, not a product substrate and not a
second command plane. Archive closeout must fuse accepted specification
obligations forward; a tool-applied delta may not silently delete existing
`WHEN`, `THEN`, or `AND` obligations without an explicit removal decision.

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
`ethos lane bind-claim`, `ethos lane refresh-base`, `ethos land`,
`ethos lane retire-landed`, and `ethos lane retire-unbound` define the local
ownership, evidence binding, stale base replay, candidate closeout, landed-lane
retirement, and unbound-ref residue cleanup paths.
Git worktree facts remain observable, but raw worktree creation is not the
standard ETHOS lifecycle state because it bypasses ETHOS lease and claim
boundaries.
When multiple agents change the repository concurrently, integration is judged
by repository truth, authority order, lifecycle legality, and bound evidence.
Candidate integration fuses or rejects conflicts by those measures; it is never
last-writer-wins and never a host-side overwrite race.
Foreign Work Lanes are product-observable and observe-only by default. Status
payloads may reveal their branch, head, lease owner, claim binding, dirty state,
path scope, coordination state, and current actor capability, but another agent
does not gain write, land, or retire authority from visibility. Write authority
belongs to the lane owner. Retiring or absorbing a foreign lane requires the
owner, an accepted handoff, or maintainer break-glass evidence. Collaboration
therefore starts as a read model over Git, lease, claim, and evidence facts; a
host-specific chat, thread, or message bus may project those facts but cannot
become the semantic center.

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
auditable without binding ETHOS to a specific host or model provider. Adapter and
profile bindings must also expose their admission authority, truth boundary, and
decision state before they can participate in the registry.

### Capability before surface

Repository operation capabilities are defined before CLI, MCP, npm, CI, Docker,
Homebrew, GitHub Action, or GitLab Component surfaces. The CLI is public UX, not
the semantic center.

### Governance before tooling

ETHOS decides why a gate runs, which evidence is sufficient, whether a result is
trusted, and whether land or publish is allowed. Tools only observe, execute, or
translate.

### Configuration boundaries

Configuration follows separation of concerns, MECE, SSOT, and DRY. Package and
workspace metadata stay in `pyproject.toml`; tool-native config belongs to the
smallest stable owner (`pytest.ini`, `ruff.toml`, or `.config/checks/<concern>/`);
hosted CI remains a provider projection over reusable scripts in `.config/ci/`;
and `system/tools.toml` records why a gate exists and where its owning config
lives. A provider file must invoke the owner instead of copying its policy.

### Proof separation

Conformance, parity, golden output, migration replay, and sample repositories
belong in an explicit proof host. They must not be scattered through runtime
packages as accidental product behavior.


## Invalid-State Taxonomy

ETHOS reduces every emitted gap to one terminal invalid-state category. This is
not a new ontology; it is the failure vocabulary implied by the kernel chain and
the substrate the chain runs on:

```text
authority_gap
subject_ambiguous
commitment_missing
change_unbounded
carrier_invalid
evidence_missing_or_stale
claim_unbound_or_overreaching
chronicle_missing
substrate_untrusted
```

The first eight categories are failed preconditions of Authority, Subject,
Commitment, Change, Evidence, Claim, and Chronicle. `carrier_invalid` is the
Change-carrier boundary: an OpenSpec workspace, change, archive, delta, or
metadata record is not valid enough to bound the transition.
`substrate_untrusted` is the execution boundary: Git, hooks, worktrees, generated
projections, command runtimes, Python/uv/node launchers, or local state cannot be
trusted enough to execute the chain. Projection drift and adapter bypass reduce
there; they do not become new truth centers.

`system/invalid_states.toml` is the machine contract. `ethos report --json`
projects the taxonomy over current gap layers so humans and agents see whether a
failure is an authority, subject, commitment, change, carrier, evidence, claim,
chronicle, or substrate problem before choosing a repair.

```text
Seven obligations judge.
Five verbs transition.
Three boundaries constrain.
Nine invalid states block.
```

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
