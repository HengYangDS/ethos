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
pile. The registry governs Markdown under the repository profile's declared
documentation root (`docs/` for ETHOS). Each selected document declares
Subject, Role, State, and Relation metadata in front matter. Skills, OpenSpec,
system contracts, and distribution files retain their own consumers; registry
metadata outside the selected root grants no authority.

A selected page may enclose that same YAML payload in a leading HTML comment
when its title must render first on a Forge. Both carriers enter the same parser;
the commented form requires an H1 as its first visible block. An incomplete
wrapper, invalid YAML, or premature HTML comment terminator blocks rather than
becoming an empty declaration. This does not change OpenSpec, Skills, or
system-axiom syntax:

```markdown
<!--
---
subject: example:guide
role: how-to
state: active
relations: {}
---
-->

# Guide
```

For active/canonical non-observational pages, the portable reader floor is a
visible H1 and non-empty text outside headings and code fences, not fixed
English `Status`, `Purpose`, or `See also` labels. An authored `Status:` claim
must not be empty or contradict `state`. Evidence and history may omit reader
guidance, but the commented carrier still requires its H1 first. This structural
floor does not certify that the text is useful or understood.

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
redundant current-surface carriers. Official OpenSpec archive bytes remain
immutable at their Git revisions; their presence in the latest tree is not a
permanent retention requirement or current authority. Retire an unconsumed
current-tree copy only after canonical specs, exact proof bindings, incoming
links, and Git recovery are checked. Age alone is not a retention or deletion
rule.

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

The portable hard ceiling is 500 nonblank physical lines per tracked, current,
authored Markdown document, including root entrypoints, rules, Skills and a
repository's native documentation root. Frontmatter, tables, code fences and
quotes count; blank-line padding and a metadata state of `archived` do not
exempt an otherwise current document. The release contract's root
`CHANGELOG.md` is cumulative release history: neither its total nor its
Unreleased or version sections have a document-length ceiling. Release format
and version meaning belong to release governance, not this length check. A
same-named document elsewhere is still ordinary authored documentation.
Official OpenSpec artifacts and their archive, and outputs with a declared
producer, are separate carriers with their own checks.

The docs-registry gate reports the exact overlong source; official OpenSpec and
generated-artifact checks retain their own obligations. This ceiling prevents
one unreadable carrier, not semantic fragmentation: split by reader question
and responsibility, preserve context and links, and test retrieval before and
after. Imported research is settled into its topic owner with source and
disposition, not copied as a raw report.

A large reduction is not presumed lossless because the old bytes remain in Git.
Before deleting or partitioning current text, map each still-live obligation to
its canonical owner, distinguish dated observations and explicitly retired
claims, and repair navigation and consumers. Keep that disposition in the
existing Change and affected documents, not a second progress ledger. If a
live obligation has no surviving owner, the reduction is incomplete.

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
length or graph coverage alone. A passing parser or report alone does not
certify reader comprehension or remote rendering.

## Directory entrypoint rule

Only README.md may carry current ETHOS-authored directory navigation, including
docs, OpenSpec, rules, skills and other source roots. Do not create index.md
alternatives or parallel directory catalogs. Topic pages may contain contextual
links without becoming directory indexes. Historical mentions, dependency
internals and external conventions do not establish current entrypoints.

`README.md` is retained only when it is the actual index, navigation entrypoint,
or semantic boundary for its directory. A directory with one substantive child
does not receive a README merely because the directory exists; an empty
directory and a marker-only README are removed. A directory with at least two
immediate navigable children needs a README with a local route into its content;
this applies to a profile-selected adopter documentation root as well as ETHOS.
Document and documentation-metadata files count as content; generated diagrams
do not. If a README contains the only
unique navigation or boundary meaning, absorb that meaning into the owning
document before deleting it.

A Decision Record is admitted only when a choice among alternatives, its
consequences, and its revisit or retirement condition remain useful across more
than one Change and cannot be expressed clearly by the current contract or
source. It is not a feedback receipt, status page, task list, or archive index.
Its filename is `dr-<four-digit-id>-<semantic-topic>.md`: the stable positive
number is never reused for another ruling, while the topic stays legible. The
Docs Registry rejects missing or duplicate current IDs without adding a
decision database. A record states its status and date, context, decision,
consequences and revisit condition; alternatives and evidence are included when
they explain the choice. Its directory README navigates records but does not
become a second decision register. Adopters need not copy ETHOS's directory
shape; their `role: decision` records follow the same identity grammar within
their selected documentation root.

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
