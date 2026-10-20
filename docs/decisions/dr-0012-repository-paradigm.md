---
subject: ethos:decision:repository-paradigm
role: decision
state: canonical
decision_id: DR-0012
decision_status: accepted
relations:
  current_owner: ../governance/config-boundary-model.md
---

# DR-0012: Repository Paradigm

Status: canonical rationale. The repository paradigm specification and its packaged contract own current behavior.

Date: 2026-10-14.

Purpose: preserve why every ETHOS-governed repository follows one common repository contract, and which structure that contract deliberately leaves to each repository.

See also: [Config Boundary Model](../governance/config-boundary-model.md), [DR-0011: Documentation portability](dr-0011-documentation-portability.md), and the `repository-paradigm` OpenSpec Change.

## Context

ETHOS governed thirteen repositories whose shared needs were encoded in incompatible ways. The 2026-10-14 inventory found:

- seven `.ethos/` file sets;
- five commit grammars;
- three branch-prefix vocabularies;
- three `.config/` taxonomies;
- four decision-record namings;
- two front-matter syntaxes;
- tool configuration spread across roots and manifests;
- orchestration through native tasks in some repositories and shell scripts in others.

ETHOS documents then said that ETHOS must not make adopter layout universal. As a result, no owner could resolve the drift, and each repository improvised. The repositories' owner directed that all ETHOS-managed repositories, ETHOS included, follow one top-down paradigm that holds only what they genuinely share.

DR-0011 had already rejected a cloned documentation tree, because path equality does not prove semantic equivalence and it forced empty carriers.

## Decision

ETHOS owns one repository paradigm and evaluates it uniformly:

- a universal core;
- ecosystem modules that apply exactly when a repository uses Python, Node or Go.

The paradigm standardizes carriers that every governed repository actually has:

- root protocol entries;
- the configuration plane, grouped by consuming tool;
- the binding file set;
- commit, branch and release conventions;
- document metadata and decision-record names;
- formatters and text normalization;
- the toolchain owner and its `bootstrap`, `fix` and `check` verbs;
- native orchestration, where the only tracked scripts are official generator output;
- the CI model for several Forges;
- names.

It never requires an empty carrier. Product and domain structure, test organization, documentation subject layout and provider shape remain repository-owned. A repository cannot declare an exception. Changing an obligation is an ETHOS Change.

## Alternatives Rejected

- **Per-repository conventions:** rejected because they recreate the drift this decision removes.
- **A cloned repository tree:** rejected for the reasons DR-0011 records; product structure differs by domain.
- **A concern-named configuration vocabulary:** rejected because multi-purpose tools make the assignment an opinion table. Tool identifiers and canonical basenames are facts.
- **Documentation without enforcement:** rejected because the inventory shows that unowned conventions drift.

## Consequences and Boundary

- A gap blocks prove, land and publish, and prewrite refuses a non-conforming path. The audit names the canonical repair.
- Every adopter migrates through its own Change and switches runtime in the same batch. The deferred alphasim and di-effect families follow later.
- Shell scripts that orchestrate verbs, gates or CI retire into native commands and owner tasks, so the same invocation runs on Windows, macOS and Linux.
- A CI step keeps a shell program only as an official installer or operating-system glue. The retention record binds it to the step's exact text, with owner, reason, platforms and target-platform evidence. Such a record admits bytes under evidence the obligation names, not a repository, so it is not an exception; review judges the evidence.
- Markdown blank lines are what the shared Prettier formatter writes for its declared inputs. The paradigm adds no layout rule of its own: an earlier rule that tightened one-block list items and laid out carriers outside those inputs was retired, because it rejected formatter-accepted layout and changed rendered list meaning.
- Bare tool invocations at a repository root no longer discover project policy. The verbs and documented editor settings carry the explicit paths.
- DR-0011 remains valid for documentation subject layout. This record only adds the metadata syntax and the decision-record name grammar.

## Evidence and Revisit

- The `repository-paradigm` Change proposal and design record the inventory and the decision for each concern.
- Its `repository-paradigm` delta specification states the observable obligations and their falsifiers.
- The `retained-ci-steps` Change records why necessary glue in a CI step is retained by record rather than by exception.
- The `markdown-layout` Change records the fleet scan behind the retired blank-line rule; `installed-product` task 4.5.6 records its retirement.

Revisit when a governed repository demonstrates a shared need that the core or a module cannot express without an exception, or when a module obligation turns out to be shared by only part of its ecosystem. Retire this record when the paradigm specification itself preserves these rejected alternatives and limits.
