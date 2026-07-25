---
subject: ethos:product-design-contract
role: policy
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

`ethos status` is the single bounded read-only view. It helps humans and agents
see where they are, what they may do, who else is present, what remains gapped,
and what should run next without minting repository truth. A hard quality gap
that blocks proof or local publication must appear as a blocking status gap.

Setup and onboarding commands are outside the transition loop:

```bash
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

## Root Constraint

ETHOS keeps this root text:

# 问道

> 道隐无名，几动于微，法乎自然；
> 生一启元，分二判势，孕三冲和；
> 万象昭幽，度协畛域，枢得环中；
> 物遂其性，化育无穷，是谓玄德。

ETHOS 为名，问道为根. This text is not an external slogan, subsystem,
feature map, or naming scheme. It is the product's root constraint on
judgment: truth stays deeper than any named tool; small disorder is treated as
an early signal; governance follows the natural shape of the repository and of
the systems it touches; distinctions are made only when they decide action;
conflict is closed through bounded change, evidence, claim, and chronicle;
hidden state is made inspectable; measures stay inside their domains; and Git,
OpenSpec, CI, local state, agents, adapters, evidence, and claims are allowed
to remain what they are rather than being absorbed into ETHOS.

Read the root text as a constraint on how ETHOS judges, not as a line-by-line
module map. The engineering reading is deliberately plain: one kernel keeps the center;
truth and projection remain separate; evidence limits claims; measures fit their
boundary; transition commands close the loop; adapters stay adapters.
`system/axioms.md` is only a machine-adjacent derivation for checks and reviews.
It does not restate the root text, does not create another truth center, and
must remain subordinate to this contract.

Engineering names therefore stay ordinary: kernel, evidence, claim, chronicle,
adapter, profile, transition loop, and axiom mean what they say.

## Semantic Kernel

ETHOS is kernel-first. The executable product model is:

```text
ChangeContract + Attestation -> RepositoryFacts -> PlanIR
```

Only `ChangeContract` and `Attestation` are persistent semantic entities.
`RepositoryFacts` is freshly observed and `PlanIR` is transient. Authority,
subject, commitment, evidence, claim, and chronicle remain duties expressed by
their fields and attestations; they are not additional object models or schemas.

The center is the **governed passage** from question to repository law: a
question is bounded to a subject, tested through evidence, judged as a change to
commitments, and then either admitted, composed, refined, superseded, retired,
rejected, or archived. A **governed commitment** is the minimal auditable
engineering handle for that passage: a bounded repository promise about a
subject under an authority. It is not a new object of attachment and not a
parallel ontology.

ETHOS does not govern mechanisms for their own sake. It governs how a question
becomes, changes, or leaves repository law. A workflow, framework, skill pack,
task graph, scenario system, spec format, or method is only a vessel when it
helps a commitment become clearer, better evidenced, safer to change, or ready
to leave.

- Authority: authority order, truth boundaries, product principles, and
  decision policy. North Star is a derived reader view, not the authority.
- Subject: the governed object, such as a path, package, domain, surface,
  evidence set, or release target.
- Commitment: the Subject's contracts, policies, specs, rules, promises, and
  durable decisions. A commitment is the thing that can become repository law.
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

Practice claims belong under this chain. They are evolution carriers that ask
whether a reusable way of working should create, compose with, refine,
supersede, retire, or be rejected from the repository's commitments. The root
question is therefore not "which mechanism should ETHOS add?" but "what question
is being governed, which commitment should survive evidence, and what should
happen to the practices and carriers around it?"

## Governed Repository

ETHOS uses one governed repository model. The governed subject is always a Git
repository. Product repositories, adopted repositories, and reference
repositories differ by profile, capability set, and proof depth; they are not
separate ontology roles and do not create separate command planes.

### Isomorphic Governance

The ETHOS product repository is governed with the `product` profile. Other
repositories are governed with their selected adoption or domain profile. The
same kernel governs both cases. The profile changes profile-specific checks,
adapters, and proof depth; it does not change the subject kind or the command
semantics. The governing form is profiles and adapters over one kernel; it is
not product cloning.

ETHOS is organization-native, not author-native. Git author, Git committer,
Work Lane holder, reviewer, maintainer, bot, team, and adopter-side owner are
distinct identity facts. Authority ranks repository truth sources; operational
admission evaluates an exact request against Commitments, Git facts, bounded
Evidence, and current state. Neither role labels nor holder strings mint reusable
permission, and no product rule may depend on one built-in person, email,
workstation path, or domain repository. In particular, the product has no
single built-in personal name that acts as an authority shortcut.
A Work Lane lease holder identifies the concrete acting instance, not merely a
provider class: `agent:codex:thread:<id>`, `agent:claude:chat:<id>`,
`agent:jetbrains:chat:<id>`, `human:shell:<id>`, and
`service:gitlab-ci:pipeline:<id>` are holder references; `codex`, `claude`, or
`ci` alone are provider labels or compatibility hints. ETHOS therefore does not add a
first-class Principal, Actor, Participant, Party, Session, or Agent registry.
Temporary cooperative write coordination remains the Lane Lease. Routine lease
renewal, resume, accepted handoff, and mechanically proven retirement stay in
ignored local state; only exceptional preservation, block, foreign or orphan
resolution, and break-glass reconciliation become evidence-bound Chronicle
decisions.
The product default is therefore an external role policy: enterprises declare
the maintainer, team, reviewer, bot, service, and adopter-side owner identities
they trust. Package metadata, active docs, tests, command defaults, and release
assets must not present any individual contributor as product authority.
Active product plans, rules, and configuration comments may describe generic
reference adopters and reusable mechanism classes, but they must not depend on
named private repositories, personal work history, or private domain products
as product authority.

Published distribution packages are part of the same boundary. They may ship
neutral launcher assets and package documentation, but they must not package
historical evidence, archived change records, host-local state, tests,
adopter-private records, local paths, or person attribution metadata as product
defaults.

Release-visible provenance is also part of the enterprise product boundary.
Dated chronicles, parity evidence, archived OpenSpec changes, history records,
and superseded decisions may preserve judged history, but they must preserve it
with neutral repository-role terms. Raw workstation paths, personal attribution,
named private adopters, private project dependency literals, and adopter-private
shadow artifacts belong in the adopter repository, an explicitly ignored local
state store, or a bounded private evidence archive outside the product
distribution surface. The ETHOS product repository may keep generic parity
fixtures such as `generic-shadow.json`; named adopter shadow evidence belongs
with that adopter's own evidence root.

Command payloads that audit or summarize repository governance expose
`governance_context`. That context records the profile, repository subject,
single-kernel flag, kernel chain, shared lifecycle commands, reader projection,
repository truth boundary, and profile or adapter
boundary.
The shared lifecycle semantics are exposed as `shared_commands` and
`transition_commands`: `ethos status`, `ethos plan`, `ethos prove`,
`ethos land`, and `ethos publish`. Read-only first-glance semantics are exposed
as `reader_projection_commands`: `ethos status`. `ethos audit --mode shape` and
`ethos audit --mode deep` select proof depth for the same governed repository
contract.

## Principles

### Authority first

Product decisions cite the Authority, user instruction, repository truth,
or accepted decisions. Reader-facing North Star language is derived from that
source and cannot override it.

### Kernel-first

Folders and packages follow the kernel chain. Package names do not create
separate truth centers.

Logical and physical architecture are isomorphic. Every active module represents
one narrow concept, one authoritative owner, and one primary reason to change.
Generic catch-all modules, mixed command registries, and coincidence-based shared
helpers are rejected unless a closed machine contract proves a genuine kernel or
report-aggregation role. Remediation absorbs, precisely renames, semantically
splits, or deletes the owner; it never preserves the old path as a facade.
This invariant covers product source, tests, tools, agent scripts, configuration,
schemas, documentation, OpenSpec, and CI. Enforcement respects each carrier's
native syntax and never treats file count, directory width, ELOC, or naming
punctuation as authority to invent a semantic boundary.

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
release_root -> accepted_root -> candidate -> work_lane -> proposal_lane. The
branch names and prefixes are configurable, but the roles are product semantics.
The configured role policy is auditable through its configuration source,
configuration keys, default-policy state, semantic role order, and configured
patterns; release_root and accepted_root are both protected roles but they are
not interchangeable.
Work Lane lifecycle commands are also product semantics: `ethos lane start`,
`ethos lane bind-claim`, `ethos lane refresh-base`, `ethos land`,
`ethos lane retire landed`, and `ethos lane retire superseded` define local
ownership, evidence binding, stale-observation, base replay, candidate
closeout, landed-lane retirement, and absorbed linked-lane retirement. The
`ethos lane retire unbound` reader preserves unbound-ref residue for separately
admitted exceptional deletion rather than treating absent registration as safe
cleanup.
Git worktree facts remain observable, but raw worktree creation is not the
standard ETHOS lifecycle state because it bypasses ETHOS lease and claim
boundaries.
When multiple agents change the repository concurrently, integration is judged
by repository truth, authority order, lifecycle legality, and bound evidence.
Candidate integration fuses or rejects conflicts by those measures; it is never
last-writer-wins and never a host-side overwrite race. If base refresh conflicts
only on head-bound generated projection evidence, ETHOS may replay repository
truth and mark the projection stale, but it must require evidence regeneration
and head-bound proof before landing.
Foreign Work Lanes are product-observable and observe-only by default. Status
payloads expose a non-authoritative `action_preview`; visibility never grants
write, land, or retire permission. Every mutation re-evaluates the exact holder,
lease ID, epoch, HEAD, policy, and evidence bindings. Routine lifecycle stays
local; exceptional foreign, orphan, preserve, block, or break-glass judgment
must first exist as accepted Chronicle evidence and is then consumed by a
recomputed two-phase resolution. Collaboration therefore starts as a read model
over Git, lease, claim, and evidence facts; a host chat, thread, or message bus
may project those facts but cannot become the semantic center.

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
smallest stable concern owner under `.config/checks/<concern>/` unless the tool or
repository substrate has no explicit-config mode;
ignored tool runtime caches belong under `build/runtime/tool-cache/<tool>/`; source-bound Work Lane virtual environments belong under `build/runtime/venv/`; provider emulator and scratch work belongs under `build/runtime/work/<provider>/`; local build artifacts belong under `build/artifacts/<kind>/`; generated proof evidence belongs under `build/evidence/`; reusable runner scripts live
under `tools/ci/scripts/`; hosted CI remains
a provider projection over those runner scripts; `local-ci` is the repository-local
fallback evidence path for the same owner gates when hosted remotes are unavailable
or delayed; and `system/tools.toml` records why a gate exists and where its
owning config lives. A provider file
must invoke the owner instead of copying its policy. Local fallback evidence
never claims hosted CI success.

### Proof separation

Conformance, parity, golden output, migration replay, and sample repositories
belong in an explicit proof host. They must not be scattered through runtime
packages as accidental product behavior. Tracked parity evidence binds both the
commit where comparison ran and the parity-relevant semantic Git tree. This lets
an evidence-recording commit prove what it actually proves without pretending to
know its own future commit hash, while any later parity-relevant source or
contract change still stales the evidence.

When a Work Lane changes that parity-relevant tree, it SHALL refresh and commit
the tracked generic parity evidence in the same admitted Work Lane after the
source commit and before executed proof. `quality evidence-freshness` SHALL
surface a stale configured generic carrier as a first-class proof gap, rather
than leaving it to an ambient unit assertion. Candidate and accepted roots stay
write-protected: landing carries the already-committed semantic evidence forward;
it is not a license to repair evidence after integration.

Generated proof artifacts are physical evidence projections, not truth stores.
When multiple local or hosted runners can write the same latest artifact, the
owner gate must serialize cleanup and writes or use an equivalent per-run
promotion protocol. The current Python test gate uses a local lock around the
coverage evidence directory so concurrent `prove` and local-CI runs cannot mix
coverage shards or publish a false latest coverage XML.

## Invalid-State Taxonomy

ETHOS may explain known gaps through a small invalid-state taxonomy. The
taxonomy is a derived reader vocabulary, not a closed ontology and not an
admission requirement for new signals:

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

`system/invalid_states.toml` is an optional explanation projection. `ethos
status --json` may group known signals for readers, but an unknown signal remains
verbatim and does not become invalid merely because the current taxonomy has not
yet evolved. Taxonomy changes follow evidence; evidence never conforms to a
closed taxonomy merely to pass a gate.

```text
Seven obligations judge.
Five verbs transition.
Three boundaries constrain.
Open signals remain visible.
```

## Truth Boundaries

Repository truth includes source code, tests, schemas, canonical docs, OpenSpec
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
Its evidence freshness is explicit: historical evidence preserves a judged fact;
head-bound and semantic-scope evidence make currentness assertions that must
fail closed when their respective binding no longer holds. No missing-freshness
compatibility mode is permitted.
Work Lanes prove local ownership and write admission. Intake providers report
projection evidence. Neither Work Lane presence nor intake completion promotes
truth by itself.

Promotion targets are provider-neutral repository paths: source, tests, docs,
schemas, canonical OpenSpec specs, or dated evidence. Dry-run proof is readiness
only. Executed proof can support promotion when selected gates record passing
exit codes and the evidence is bound to a claim.

## Build And Release Contract

The active build contract is:

```text
uv workspace = dev, lock, run, and test orchestration
Hatchling = canonical PEP 517 build backend for Python packages
wheel/sdist = local smoke artifacts
PyPI/TestPyPI = deferred Python release channel, not active scope
npm = deferred thin launcher only, not a second implementation
Homebrew/Docker/CI = deferred distribution or runner adapters, not active scope
```

The active local closeout phase explicitly does not perform PyPI/TestPyPI
publish, npm registry publish, Homebrew publish, Docker/OCI push, GitHub Action
marketplace publish, GitLab Component publish, or remote Git push. Those are
separate publication adapters and require their own evidence when activated.

Status: see front matter.

Purpose: explain the repository truth represented by this ETHOS document.

See also: [Documentation Index](../index.md), [Command Plane](../reference/command-plane.md), and [Glossary](../reference/glossary.md).
