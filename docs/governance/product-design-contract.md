---
subject: ethos:product-design-contract
role: decision
state: canonical
relations:
  canonical_for: product truth, migration boundary, and self-governance design
---

# Product Design Contract

ETHOS means Evidence-grounded Trust for Human-Agent Operational Stewardship.
ETHOS is the evidence-grounded operating layer for human-agent repository
change.

The product answers seven operational questions:

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

Advanced workflows stay under `ethos ...`:

```bash
ethos init
ethos adopt
ethos doctor
ethos campaign
ethos intake
ethos quality
ethos assistants
ethos playbooks
ethos report
```

## Kernel Chain

ETHOS is kernel-first. The product model is:

```text
Constitution -> Subject -> Contract -> IR -> Transition -> Inscription -> Evidence -> Chronicle -> Evolution
```

- Constitution: authority order, truth boundaries, public command plane,
  workspace discipline, and context policy.
- Subject: the governed object, such as a path, package, domain, surface,
  claim, evidence set, or release target.
- Contract: policy, claim, spec, domain contract, quality rule, release rule, or
  adapter contract that applies to a Subject.
- IR: changed scope, risk classes, required gates, evidence requirements, and
  explanations.
- Transition: state movement from one repository condition to another, including
  lane, land, publish, authorization, and expected HEAD.
- Inscription: source, docs, config, evidence, projection, or artifact written by
  a transition.
- Evidence: gate runs, digests, HEAD binding, claim binding, CI proof, and
  attestations.
- Chronicle: durable decisions, closeouts, campaign events, and retirement
  records.
- Evolution: gaps, hypotheses, profile improvements, and retirement proposals.

## Principles

### Kernel-first

Folders and packages follow the kernel chain. Existing package names are
migration hosts until they match the target ontology.

### Contracts before providers

Provider-neutral contracts precede implementation. Git, OpenSpec, Backlog, MCP,
ACP, Superpowers, GitHub, GitLab, Dagger, Pants, SLSA, pytest, Ruff, and pixi
are adapters or providers, not ontology anchors.

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

Superpowers is an external method pack. Codex memory, fast mode, goals,
subagents, and doctor signals are host-local or session capabilities. MCP, ACP,
IDE surfaces, and assistant context bundles are context providers or runtime
projections. Agent output is never repository truth until promoted into tracked
artifacts and evidence.

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
