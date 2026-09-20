---
subject: ethos:docs-registry
role: explanation
state: canonical
relations:
  canonical_for: documentation governance
---

# Docs Registry

Status: canonical.

Purpose: define one mechanically checkable documentation structure and the
placement rules that keep each current meaning under one owner.

See also: [Documentation Root](../README.md),
[Product Design Contract](product-design-contract.md),
[Terminal Governance Product Design](../plans/terminal-governance-product-design.md),
and [Command Plane](../reference/command-plane.md).

ETHOS documentation is governed as sedimented knowledge, not as a loose page
pile. Every governed document declares Subject, Role, State, and Relation
metadata in front matter.

`ethos prove --gate docs-registry --json` is the reader-facing and machine
quality entrypoint.
Missing metadata is a required gap because agents need to distinguish canonical
truth, active workflow notes, planned material, experimental material, and
archived history before they act.

`ledger` is not a document role. Raw feedback, transcripts, host memory, agent
summaries, generated classifications, and temporary recovery matrices are
non-authorizing inputs. A bounded recovery uses one official OpenSpec Change to
classify each distinct obligation as accepted, superseded, pending verification,
or rejected. Accepted meaning then moves to the Product Design Contract, the
Terminal Governance Product Design, a necessary Decision Record, or its native
executable owner; the recovery material is deleted after coverage proof.

The registry lifecycle is:

```text
observe -> shape -> canonize -> project -> retire
```

Archive material may preserve old vocabulary. Canonical docs must lead with the
single `ethos ...` command plane.

Superseded documents live only as explicit `docs/history/` carriers. Current
architecture, governance, reference, guides, and plan surfaces must not retain
redirect or locator pages for retired concepts; they link directly to the
historical carrier when historical context is necessary. Retirement removes
only the redundant current-surface carrier, never immutable OpenSpec archives
or historical evidence bytes.

## Semantic Authority And Carrier Boundaries

Files, directories, formats and tools are carriers, not origins of authority.
Authoritative instructions and accepted decisions establish intended meaning;
observed execution establishes scoped facts. Select the owner by responsibility
and reason to change, not by filename or storage location.

| Meaning | Unique owner | Other carriers |
| --- | --- | --- |
| Product mission and foundational invariants | Product Design Contract | Explain and reference rather than independently redefine. |
| Accepted observable capability requirements | Official OpenSpec capability specifications | Docs explain and navigate the requirement, not a second editable contract. |
| Proposed change, alternatives, experiment procedure and migration | Selected Change proposal, delta specs and design | Research supplies attributed findings, not undeclared approved scope. |
| Bounded task progress | Official Change tasks | The terminal plan orders dependencies and exits without copying checkbox state. |
| Executable behavior and policy | Existing implementation, schema or native configuration | Adapters and generated views consume the owner. |
| Observed execution, proof and effects | Exact evidence and necessary Attestations | Reports cite facts; acceptance, installation and publication remain separate. |
| Reusable explanation, guidance and sourced synthesis | Relevant docs topic | Link supporting authorities; do not create another workflow or proof store. |
| Irreducible cross-Change rationale | One necessary decision record | Name the current owner; history does not grant permission. |
| Directory orientation | A necessary README.md | Derive navigation views; no index.md directory entrypoint. |

SSOT means one editable owner per proposition, not one file for everything.
MECE separates responsibilities and covers in-scope obligations without denying
their relationships. DRY removes independent copies of knowledge, not clearly
sourced explanations. Apply SOLID through cohesive responsibilities, small
consumer contracts, replaceable projections and dependency on semantic interfaces.

Product invariants constrain capability requirements; implementation is checked
against them. Contradictions remain explicit defects, not resolved by selecting
the convenient carrier. An obligation changes through its accepted Change and
affected consumers are updated. Acceptance of a requirement does not prove that
the implementation or deployment satisfies it.

OpenSpec specs are durable behavior contracts, not temporary notes. Docs research
may evolve, but experiment acceptance and progress belong in the Change. Native
OpenSpec artifacts retain their own schema, not mandatory docs frontmatter.
Use official context, rules, instructions, status, validation and archive; extend
the artifact schema only for a proven artifact or dependency gap. OKF exchange
is a consumer, not another source of accepted intent.

## Semantic Organization And Progressive Disclosure

One semantic authority does not require one physical file. Group related
subjects in meaningful subdirectories when readers can select a narrower
question without first reading unrelated material. An overview owns the purpose,
current conclusion and navigation; topic documents own their detailed meaning.
Other documents reference that owner rather than restating its requirements.

Split at reader tasks and independent semantic responsibilities, not after a
fixed number of lines. Preserve necessary context, counterexamples, provenance
and interpretation limits. A design explains choices; an official task artifact
tracks execution; a plan states dependencies and exits; dated observations do
not silently become current product truth. Do not move unresolved obligations
to history merely to shorten a current document.

Document size is a diagnostic, not a semantic-completeness score. Report prose,
tables, code/examples, citations and whole-file size separately. Source line
wrapping, markup and language differences must not masquerade as reading cost.
Check the largest independently readable section and whether readers can find
a current decision, its rationale and the next action without scanning unrelated
history. A short but fragmented or duplicated document can still fail that test.

No universal 100/200/300 effective-length ceiling is adopted. Any future length
gate requires a named reader task, a repeatable measurement, distinct document
roles, falsifying examples and before/after retrieval evidence. Current oversized
mixed-responsibility documents can be reorganized without waiting for a numeric
threshold. Imported research is settled into its topic owner with source and
disposition preserved; copying raw reports or recording hashes alone is not
complete semantic absorption.

## Purpose And Quality

Documentation preserves meaning, reduces uncertainty, and supports correct
understanding, decisions and action. It is not a warehouse of text or a formatting
exercise. Quality follows fidelity, intelligibility and elegance, in that order.

- Fidelity: distinguish facts, assumptions, proposals and accepted requirements;
  preserve scope, counterexamples and provenance. Do not imply complete delivery
  from a diagram, a label or a passing parser.
- Intelligibility: organize around reader questions, explain prerequisites and
  exceptions, and make current meaning discoverable through progressive detail.
  Human reading and agent retrieval must reach consistent supported conclusions.
- Elegance: use precise terminology, cohesive structure and restrained expression.
  Remove redundancy and incidental complexity without sacrificing necessary
  meaning. Shortness, symmetry and metadata volume are not quality goals.

## Human And Agent Reading Contract

The same accepted meaning serves both readers. Pages and structured metadata
provide complementary access, not separately edited authorities. Plain Markdown
must remain useful; a rendered view cannot hide required meaning behind
interaction, and agent retrieval cannot drop conditions to fit a context budget.

- Start with the reader question, scope and concise answer; expand into rationale,
  examples, exceptions and source evidence.
- Keep enough local context for independent understanding. Link prerequisites
  instead of copying them, without forcing a chain of tiny pages for one rule.
- Directory depth expresses real subject containment. Cross-cutting questions
  use meaningful links, not copied pages or mirrored trees.
- Link labels identify the target question or obligation. Prefer a relevant
  stable section. Orientation, prerequisites, related concepts and evidence are
  distinct navigation roles.
- Keep one authored relation source. Derive breadcrumbs, backlinks and machine
  indexes when useful; do not manually maintain a second sitemap or ontology.
  Prohibited cycles depend on relation meaning, not merely graph shape.
- Moves update incoming links and anchors while preserving subject identity and
  necessary historical references. Deletion cannot strand a requirement or its
  only rationale.

Metadata is a typed contract: stable subject, document purpose, lifecycle and
meaningful relations. Provenance and applicability depend on the claim.
Fields without consumers are not mandatory decoration. Derive display/history
data where already owned; avoid independent copies of status, title or version.
Lifecycle labels never grant authority or prove currentness.

Use one semantic/schema owner with native YAML parsing, structural validation
and relationship resolution. Required targets resolve; distinguish paths,
subjects, external sources and descriptive scopes rather than guessing.
Preserve unknown imported fields as inert data. OKF maps these distinctions
without replacing native acceptance; see the
[source-backed assessment](../research/foundations/documentation.md).

Acceptance covers rendered reading, raw Markdown and agent retrieval: find the
current rule, rationale, limitations and supported next action. Measure correct
answers, source selection, context volume, backtracking and time, not file
length or graph coverage alone. Current parser, relationship and visible-status
defects remain tracked in the existing Change; this contract does not claim
that every check already enforces these outcomes.

## Directory entrypoint rule

Only README.md may carry current ETHOS-authored directory navigation, including
docs, OpenSpec, rules, skills and other source roots. Do not create index.md
alternatives or parallel directory catalogs. Topic pages may contain contextual
links without becoming directory indexes. Historical mentions, dependency
internals and external conventions do not establish current entrypoints.

`README.md` is retained only when it is the actual index, navigation entrypoint,
or semantic boundary for its directory. A directory with one substantive child
does not receive a README merely because the directory exists; an empty
directory and a marker-only README are removed. If a README contains the only
unique navigation or boundary meaning, absorb that meaning into the owning
document before deleting it.

A Decision Record is admitted only when a choice among alternatives, its
consequences, and its revisit or retirement condition remain useful across more
than one Change and cannot be expressed clearly by the current contract or
source. It is not a feedback receipt, status page, task list, or archive index.
Its filename is lowercase and semantic rather than a numbered identity.

## Markdown list structure

List spacing expresses block structure, not editing chronology. A list whose
items each contain one paragraph is compact; wrapping that paragraph across
source lines does not make it multiple paragraphs. Preserve necessary blank
lines between paragraphs and other blocks inside compound items. Keep sibling
spacing consistent within a list, and evaluate nested lists independently.
Literal examples in code blocks are content, not formatting targets.

These rules apply to current Markdown throughout the repository, including
official OpenSpec artifacts; they do not replace OpenSpec's artifact ownership.
Historical evidence is audited but cannot be rewritten merely for presentation.
Any correction must preserve words, links, item order, task states, and block
nesting. Successful parsing or native Markdown lint alone does not establish
this consistency; executable enforcement remains a tracked terminal-plan gap.

## Portability Boundary

Product requirements and reusable procedures describe repository capabilities,
roles and observed conditions, independently of a particular adopter. Concrete
repository names belong to attributed research, reproducible cases or historical
evidence; they identify the source, not an integration dependency or a special
policy. Synthetic examples use descriptive sample identities. Named native tools
remain appropriate where their actual protocol or behavior is the subject.

The registry owns portable document metadata, role/state vocabulary, taxonomy
extensions, visible sections, command examples, and plan discoverability. It
reads the documentation root declared by the adopter profile, defaulting to
`docs/`; it does not require ETHOS's physical directories.

ETHOS's own physical documentation shape is a product self-audit concern. It is
not an adopter contract and is not exposed as a second topology gate. An
adopter may organize its documentation by its native subject domains while
retaining the same metadata and authority semantics.
