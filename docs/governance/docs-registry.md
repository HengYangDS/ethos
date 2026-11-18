---
subject: ethos:docs-registry
role: policy
state: canonical
relations:
  canonical_for: documentation governance
---

# Docs Registry

Status: canonical.

Purpose: define one mechanically checkable documentation structure and the
placement rules that keep each current meaning under one owner.

See also: [ETHOS source Documentation Root](../README.md "source-only"),
[Product Design Contract](product-design-contract.md),
[ETHOS source Terminal Governance Product Design](../plans/terminal-governance-product-design.md "source-only"),
and [Command Plane](../reference/command-plane.md).

ETHOS documentation is governed as sedimented knowledge, not as a loose page
pile. The registry governs Markdown under the repository profile's declared
documentation root (`docs/` for ETHOS). Each selected document declares
Subject, Role, State, and Relation metadata in front matter. Skills, OpenSpec,
system contracts, and distribution files retain their own consumers; registry
metadata outside the selected root grants no authority.

Plain front matter is the only metadata carrier. A selected page whose YAML
payload sits inside a leading HTML comment declares no metadata; the repository
paradigm reports the wrapper, and `ethos lane repair-paradigm --apply` removes it.
This does not change OpenSpec, Skills, or system-axiom syntax.

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

Git retains superseded document bytes. Keep a `docs/history/` carrier only when
its historical explanation or retrieval instructions have a current consumer;
otherwise cite the exact Git revision. Current architecture, governance,
reference, guides, and plan surfaces must not retain redirect or locator pages
for retired concepts. Retirement removes redundant current-surface carriers.

When a genuine original must remain byte-exact, its documentation taxonomy
declares one `retained` member: exact path, subject, `history` or `evidence`
role, allowed source state preserved without relabeling, full `commit:path`
origin, independent live `relations.current_owner`, review date and executable
exit condition.
The native Git/content observer verifies a regular blob, complete bytes and
mode without following links. Missing, changed, unavailable or conflicting
origins are required gaps; a declaration alone is not verification. The pure
registry receives that observation rather than importing an IO adapter.

Length, native formatting/lint, prose and links derive current authored inputs
from that same verified registry and declared generated-output owners. A
directory name or lifecycle label is not an exemption. Current authored Skill
references retain their Skill package and formatter owners, not historical
status. Official intent stays OpenSpec-owned; only exact dated archive members
are immutable history. The release-owned root changelog keeps release format
checks but has no document-length ceiling. Retained originals keep registry
and consumer checks; they are never silently rewritten for presentation.
Current navigation also uses the shared authored selection: a verified original
README remains discoverable history, but is not a current entrance or a
substitute when current children need one.

Official OpenSpec archive bytes remain
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

| Meaning                                                           | Unique owner                                            | Other carriers                                                                  |
| ----------------------------------------------------------------- | ------------------------------------------------------- | ------------------------------------------------------------------------------- |
| Product mission and foundational invariants                       | Product Design Contract                                 | Explain and reference rather than independently redefine.                       |
| Accepted observable capability requirements                       | Official OpenSpec capability specifications             | Docs explain and navigate the requirement, not a second editable contract.      |
| Proposed change, alternatives, experiment procedure and migration | Selected Change proposal, delta specs and design        | Research supplies attributed findings, not undeclared approved scope.           |
| Bounded task progress                                             | Official Change tasks                                   | The terminal plan orders dependencies and exits without copying checkbox state. |
| Executable behavior and policy                                    | Existing implementation, schema or native configuration | Adapters and generated views consume the owner.                                 |
| Stable operational boundaries                                     | Applicable rule owner                                   | Skills route methods; native checks enforce decidable constraints.              |
| Reusable task methods                                             | One applicable Skill and its selected references        | Consume native owners; do not duplicate policy, acceptance or progress.         |
| Reproducible failure and distinguishing expectation               | Regression at the responsible behavior owner            | Check accepted meaning, valid controls and relevant unknown/recovery paths.     |
| Observed execution, proof and effects                             | Exact evidence and necessary Attestations               | Reports cite facts; acceptance, installation and publication remain separate.   |
| Reusable explanation, guidance and sourced synthesis              | Relevant docs topic                                     | Link supporting authorities; do not create another workflow or proof store.     |
| Irreducible cross-Change rationale                                | One necessary decision record                           | Name the current owner; history does not grant permission.                      |
| Directory orientation                                             | A necessary README.md                                   | Derive navigation views; no index.md directory entrypoint.                      |

A document is normative only when it is the Product Design Contract or a higher owner links it as
the owner of a named subject, as the terminal plan does for this registry's documentation contract
and the Product Design Contract does for the Module Layout Rules and the Engineering Axioms. Every
other document explains, instructs, navigates or records, and links its owner instead of
restating it.

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

Preserve useful knowledge where its next reader can act on it, not as a copy of
the conversation. A lesson can require an owner correction and a regression;
that relationship is not duplicated policy. Add rationale or a procedure only
when it changes a later decision. Keep conditions, exceptions, evidence scope
and the replaced remedy recoverable through that owner and Git history.
Raw transcripts and machine memory support retrieval, never current authority.
Open obligations remain in the existing Change; a handoff derives them rather
than creating a second ledger. See [ETHOS source Learning And Change Relations](evolution-campaign.md "source-only")
for repository-first continuation and domain transfer.

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

The portable ceiling is the repository paradigm's Markdown ceiling: by default
500 nonblank physical lines per tracked, current, authored Markdown document,
including root entrypoints, rules, Skills and a repository's native
documentation root. A repository may declare its own value for the whole
repository in `.ethos/rules.toml` `[paradigm.size]`, within the paradigm's
bound; a higher value needs its reason. No value applies to one document.
Frontmatter, tables, code fences and quotes count; blank-line padding and a
metadata state of `archived` do not exempt an otherwise current document.
The release contract's root `CHANGELOG.md` is cumulative release history:
neither its total nor its Unreleased or version sections have a
document-length ceiling. Release format and version meaning belong to release
governance, not this length check. A same-named document elsewhere is still
ordinary authored documentation.
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
- Elegance: `雅` as the [Product Design Contract](product-design-contract.md#evidence-planes-and-completion-claims)
  defines it, judged in the rendered whole. Precise terminology, cohesive structure and restrained
  expression support it; remove redundancy and incidental complexity without sacrificing necessary
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
[optional source-backed assessment](../research/foundations/documentation.md "source-only").

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

`README.md` is retained only when it is the actual index and navigation entrypoint
for its directory: it declares `role: index`, states the directory's purpose and scope, routes to
its children and holds at most 100 nonblank lines; policy, procedure, evidence and history live
on named pages. A directory with one substantive child
does not receive a README merely because the directory exists; an empty
directory and a marker-only README are removed. A directory with at least two
immediate navigable children needs a README with a local route into its content;
this applies to a profile-selected adopter documentation root as well as ETHOS.
Document and native TOML/JSON documentation-metadata files count as content; generated diagrams
do not. If a README contains the only
unique navigation or boundary meaning, absorb that meaning into the owning
document before deleting it.

## Decision records

A decision record keeps WHY: a choice among alternatives, its consequences and the condition
under which it is looked at again. It is written only when that reason remains useful across
more than one Change and the current contract or source cannot say it. It never owns current
behavior: it names the current owner that does. It is not a feedback receipt, a status page, a
task list or an archive index. A record enters the tree decided, through an accepted Change; a
proposal lives in OpenSpec and is no record. Mechanical validation does not decide whether a
choice is sound or worth preserving.

Every governed repository writes its decision records in this one form. The form follows the
architecture decision record of its common template (a directory of numbered records, numbers
never used twice, a status and a date in the front matter, an old record kept and marked) and
departs from it where the table says so.

| The common template                                                  | This form                                                                                 | Why it departs                                                                     |
| -------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| directory `docs/decisions`                                           | `docs/decisions`                                                                          | the same                                                                           |
| file `NNNN-title.md`                                                 | `dr-NNNN-<topic>.md`                                                                      | the prefix is this fleet's accepted name grammar                                   |
| key `status`                                                         | key `decision_status`                                                                     | every released engine requires this key; the values are the template's             |
| proposed, rejected, accepted, deprecated, superseded                 | accepted, superseded, deprecated, rejected                                                | a record enters the tree decided; OpenSpec holds proposals                         |
| `date`: when the decision was last updated                           | `date`: the day of the decision                                                           | a record is fixed at acceptance, and the day it stopped governing is in its banner |
| decision-makers, consulted, informed                                 | named by role in "Evidence and Revisit"                                                   | rules bind roles, not persons                                                      |
| no other key                                                         | `subject`, `role`, `state`, `decision_id`, `relations`                                    | the metadata that every document of this registry carries                          |
| one relation, superseded by                                          | `supersedes` and `updates`, each with its reverse                                         | the template has no word for a record that replaces a part                         |
| context, drivers, options, outcome, consequences, confirmation, more | Context; Decision; Alternatives Rejected; Consequences and Boundary; Evidence and Revisit | the fleet's five sections hold the same matter and are already checked             |

### Where and what

- **Directory.** `docs/decisions/`: the directory `decisions` directly under the documentation
  home, which is `docs` unless the profile declares another, in every repository that has a
  record. It holds the records
  and one `README.md`, and nothing else: no directory inside it, no template, no companion page
  and no second series. A repository without a record has no such directory.
- **File.** `dr-NNNN-<topic>.md`: four digits and a lower-case kebab-case topic. The number is
  the highest in the directory plus one, taken when the record is committed in its lane. No
  number is reserved. When two lanes take the same number, the one that lands second takes the
  next. A number is never used twice and no record is ever removed.
- **Front matter.** These keys, in this order, and no other:

  | Key               | Value                                                                                                                                                                                                                                                                                 |
  | ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
  | `subject`         | `<repository>:decision:<topic>`, with the file's topic                                                                                                                                                                                                                                |
  | `role`            | `decision`                                                                                                                                                                                                                                                                            |
  | `state`           | `canonical`, always: the file is the one carrier of its record, whatever became of the decision                                                                                                                                                                                       |
  | `decision_id`     | `DR-NNNN`, the file's number                                                                                                                                                                                                                                                          |
  | `decision_status` | `accepted`, `superseded`, `deprecated` or `rejected`                                                                                                                                                                                                                                  |
  | `date`            | `YYYY-MM-DD`, the day of the decision                                                                                                                                                                                                                                                 |
  | `relations`       | `current_owner`, always: the contract, specification or source that owns current behavior. Where they hold: `supersedes`, `superseded_by`, `updates`, `updated_by` (each one record or a list), `formerly` (an identity in an older series) and `restored_from` (a commit and a path) |

- **Body.** The title `# DR-NNNN: Title`. Then, only in a record that no longer governs, one
  banner as a quotation, and the same banner again under each section heading. Then free text.
  Then exactly five sections in this order, each with readable rationale: Context; Decision;
  Alternatives Rejected; Consequences and Boundary; Evidence and Revisit. "Evidence and
  Revisit" names who decided, by role. No record writes a status or a date line in its body:
  the front matter is their one carrier. Plain prose, rationale lists, quotations, tables, bare
  identifiers and evidence paths are valid. Task checkboxes, code blocks, embedded HTML and
  executable procedures belong to their producing Change, how-to or native record. Invocation
  inspection parses syntax without executing it; ambiguous inline execution is refused rather
  than reported as proved absent.
- **Index.** `docs/decisions/README.md` holds one sentence on what the directory is, a pointer
  to this contract, one table and one legend line. The table has three columns (the record's
  number and title, linked; its status; its date) and one row for each number from 1 to the
  highest. A number without a file has a row that says why. The legend is the same line in
  every repository. The index holds no rule text.

A record in force:

```yaml
---
subject: example:decision:storage-engine
role: decision
state: canonical
decision_id: DR-0004
decision_status: accepted
date: 2026-03-02
relations:
  current_owner: ../../openspec/specs/storage/spec.md
---
```

The record that superseded it, and the old record after it:

```yaml
decision_id: DR-0009
decision_status: accepted
date: 2026-09-14
relations:
  current_owner: ../../openspec/specs/storage/spec.md
  supersedes: DR-0004
```

```yaml
decision_id: DR-0004
decision_status: superseded
date: 2026-03-02
relations:
  current_owner: ../../openspec/specs/storage/spec.md
  superseded_by: DR-0009
```

```markdown
# DR-0004: One Storage Engine

> Superseded by [DR-0009](dr-0009-two-storage-engines.md) on 2026-09-14. This record no longer
> governs.
```

The index:

```markdown
| Record                                                   | Status                       | Date       |
| -------------------------------------------------------- | ---------------------------- | ---------- |
| DR-0003: reserved and never written                      |                              |            |
| [DR-0004: One storage engine](dr-0004-storage-engine.md) | Superseded by DR-0009        | 2026-03-02 |
| [DR-0005: Retries are bounded](dr-0005-retries.md)       | Accepted, updated by DR-0011 | 2026-04-20 |

Accepted: in force. Superseded: a later record replaced it whole. Deprecated: no longer in force,
with no successor. Rejected: a ruling not to adopt, in force. A record that updates another
replaces or adds to a marked part of it.
```

### The life of a record

1. **Fixed at acceptance.** The whole file. Afterwards it changes only by a repair with no
   change of meaning (a path, a link, a renamed term, spelling, layout); by a change of the topic
   in its name, with its `subject` and the links; by the marks below; and once, in the Change
   that brings a repository to this form, by its front matter brought to the keys above, its
   body's status and date lines taken out, and a record in force rewritten into the five
   sections without a change of its ruling. A record with no date of its own takes the day its
   file was first committed on the accepted branch.
2. **A changed ruling is a new record,** which declares one of two relations. The test is asked
   of the old record: once the new one is accepted, does the old record still say something in
   force that the new one does not carry? No: the new record `supersedes` it. Yes: it `updates`
   it.
3. **Updated in part.** The old record stays accepted. It gains `updated_by` and, right after
   each sentence or list item that the new record replaces or adds to, the words "(Replaced by
   DR-M.)" or "(Added to by DR-M.)" with the link. A sentence or list item carries at most one
   such mark: its next change is a record that restates and supersedes. Where two records had
   changed one sentence before a repository took this form, its one mark names both, the
   earlier first.
4. **Superseded.** The new record can be used alone: it restates what it keeps, lists what
   differs, and its "Alternatives Rejected" carries the old ruling and each alternative that the
   old record rejected and that stays rejected. The old record stays in the directory with the
   status `superseded`, `superseded_by` and the banner. A record that only updated it and cannot
   be read without it is superseded with it.
5. **Deprecated.** No successor: the subject is gone, or the reason now lives with the current
   owner. The banner says which: "Deprecated on DATE: REASON. This record no longer governs."
6. **Rejected.** A ruling not to adopt something, kept so that it is not proposed again. It
   enters the tree with that status and is in force until a later record supersedes it, so it
   has no banner. A proposal that is simply dropped leaves no record.
7. **Nothing leaves.** A record is never removed. A record that was once on the accepted branch
   and was removed before this form comes back as it last was, with its front matter brought to
   the keys above, `restored_from`, and the banner, whose date is the day it stopped governing.
8. **The five sections bind a record in force,** accepted or rejected. A record that no longer
   governs keeps the sections it was written in.

A record names a Change by writing the Change's identifier in inline code. A record that names
an active Change binds it: the Change cites the record, by its `DR-NNNN` identity or its file
name, in one of its artifacts before it archives, and archive readiness otherwise refuses it
with `openspec_decision_uncited`. A mention in prose names nothing.

### Until an engine reads the four statuses

A released engine before that change refuses every status but `accepted`. So that no file ever
contradicts itself, a repository on such an engine does everything that leaves a status alone:
the directory's content, the name, the keys and their order, `date`, `current_owner`, bodies
without status and date lines, the index's table, and the updates with their marks. A record
that is superseded, deprecated or rejected, and a record that comes back, takes its status, its
relation and its banner together, in one Change, once the repository's engine reads them; until
then it stays as it is and its index row says "returns with the engine that reads its status"
where the file is absent. Once a repository has written a status other than `accepted`, its
engine pin does not go back below that release. Non-decision roles retain the common metadata
floor without these fields or sections.

## Markdown list structure

List spacing expresses block structure, not editing chronology. The shared
Prettier formatter's output defines spacing for its declared inputs, so a loose
list that it keeps stays loose; wrapping a paragraph across source lines does not
make it multiple paragraphs. Preserve necessary blank
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

Installed product navigation retains required links inside the version-matched
package. A Markdown link titled `source-only` is optional ETHOS development or
research context, not an installed prerequisite. Its visible label identifies
that scope. Do not label a required authority, method or acceptance dependency
optional merely to hide a missing resource; repair its source owner or include
the required input. Source-only references remain valid in the source checkout.
