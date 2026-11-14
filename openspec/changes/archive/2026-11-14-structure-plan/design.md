# Design

Line references are to `dev` at `b10254f87`: PDC the product design contract, RP the
`repository-paradigm` specification, RG `repository-governance`, cb the archived `common-base-plan`
design, ML `rules/module-layout.md`, DR-n a decision record. AR, the owner-approved end-state
design, and SL, the semantic-layout design of 2026-10-31, are ignored scratch and evidence only.
Every figure is ETHOS's own, measured at that base; other governed repositories appear by shape
only, and the fleet census of 2026-11-13 is unpublished. Inference and opinion are marked.

Three seats reviewed three drafts in four rounds and approved this text; DR-0027 records the
decision and the owner's three decisions of 2026-11-14. Sections keep the approved draft's numbers,
so references between them hold. An identifier in parentheses (SA, SD, SE or ES and a number) names
the review finding a sentence answers, and local review records hold the mapping. No finding was
declined without the measurement that refutes it (SE27, on the unit of the counter).

## Context

### 1. Direction and what is already decided

The owner asked on 2026-11-13 for the common semantic organization of every governed repository,
extracted from all of them and enforced as a strong constraint of the common base, so arbitrary,
flat and unordered trees stop appearing. Decided on the same date: it reports first, new violations
are refused one release after the report, existing stock blocks after 0.2.0 on a dated burn-down, a
new direction queues behind the release-candidate path, and a "frozen" repository state exists.

This design is the common base's fifteenth family (cb, Base table). It reverses or modifies the
texts 12.1 lists: PDC:334-337 and :474; RP:24 to :35, :654-659, :666-668, :682-684 and :702-704;
RG:1550-1555; DR-0012:58 and :76; DR-0011:42-44 and :64-67 with
`docs/governance/docs-registry.md:355-358` and `docs/README.md:62-64`; and, only if the owner arms
S5, ML:26-27 and :80, `rules/agents.md:68-70` and DR-0010:141-142. ML:73-75 is reversed only in one
conditional form, S7 armed against packages, which this design does not do (5).

#### 1.1 Prior design and owner requests

The owner had asked on 2026-10-31, in the author's translation: every file is organized by meaning
in a reasonable directory, semantic subdirectories included; piled-up suffixes and scattered flat
layouts are forbidden; this is a common requirement; a file that must be split is organized into
semantic subpackages by strong logic. The 2026-11-13 direction restates it as a base constraint.

A design answered it that day (SL, draft 2), and AR schedules it as `semantic-layout-moves` then
`semantic-layout`, with a record narrowing DR-0011 and DR-0012 (AR:1455, :1664). DR-0027 and 12.2's
Changes supersede those. Each obligation takes one disposition:

- **Checks 1 to 3, names** (content-free words, split residue, a restated parent segment). They go
  to the owner of names the owner decided (11.2).
- **Check 4, families** (three or more names in one directory share a run of segments). The same
  owner. ETHOS: 10 of 29 files in `src/ethos/adapters/repo` begin `git`, 5 of 34 loose files in
  `tests/unit/cli` begin `test_lane`; no rule here takes it (14).
- **Check 5, residue files.** A search of the product source found no shipped rule (inference); its
  natural owner is the repository-hygiene gate, not this family.
- **The width ceiling of its draft 1.** Superseded: that committee withdrew it because counts are
  not authority (`rules/agents.md:68-70`); S5 put it to the owner (11.1).

### 2. Facts (ETHOS, measured at `b10254f87`)

- **Tree.** 2,846 tracked files, 1,566 (55%) under `openspec/changes/archive/`, uncounted below;
  1,280 files and 266 directories outside it, 201 outside protocol carriers. Seven non-dot roots
  outside protocol carriers: five homes (`docs`, `rules`, `system`, `tests`, `tools`), one source
  root (`src`), and `assets`, which S1 reports until declared or moved.
- **One-file directories.** 63 before classes are told apart, 41 of them protocol-carrier slots;
  with S4's set-asides, 47 outside protocol carriers hold one file. 23 hold a marker beside one
  module: 22 under `src`, one under `tests`. Three disorders go to review because the tree cannot
  decide them: a name stating no concept, one concept under two names, and a wide container.

| Rule | ETHOS stock under this design's wording of the rule (5)                           |
| ---- | --------------------------------------------------------------------------------- |
| S1   | 1: `assets`                                                                       |
| S2   | 0: the profile declares no record root                                            |
| S3   | 23 of the 47 (6 `docs`, 1 `system`, 16 `tests`); 2 pass; 22 packages only counted |
| S4   | 29 containers, 302 loose files: 28 under `tests` with 301, 1 under `docs` with 1  |
| S5   | 9 directories above 20 units; median 4, 95th percentile 20, 99th 34, largest 38   |
| S7   | 3: two under `src`, one under `tests`; two packages leave S7 to ML 1.2            |

## Goals / Non-Goals

**Goals.** One semantic organization for every governed repository, following from three invariants
and decided from the tracked tree and existing declarations; an enforcement order that reports
first, refuses a new gap one release later and blocks stock after 0.2.0 on a dated burn-down table;
and ETHOS's own tree clean before any adopter's dated row.

**Non-Goals.** Code, tests or a specification delta in this Change: each row of 12.2 opens as its
own Change, none with code before 0.2.0 (12.3). A fixed tree: no rule requires a directory, and
subjects, their names and axes stay each repository's. A width bound and a name list (11).

## Decisions

### 3. The invariants

Three invariants; five of the seven rules apply one. The owner asked for invariants from which cases
follow, so a rule following from none is a named prohibition with its own decision (11).

- **I1, meaning at the root.** Every tracked root directory has exactly one meaning, and its name
  states that meaning; the meaning is decidable from the tree and existing declarations. A root is a
  home whose name a shared responsibility binds, a source root of an applied module, or a product
  root the profile declares with one line.
- **I2, one home per responsibility.** A shared responsibility has one root. Documents, rules and
  Skills each have one home, a single profile value; records lie under the docs home, the root
  `evidence` home or the archive; tests have one root where the ecosystem keeps them outside the
  package. A second root under another name is a review finding, not a gap.
- **I3, containment.** Depth expresses containment: a directory exists because it holds two or more
  entries of one level, or because its name carries a responsibility or a key that its content
  cannot carry, or because its siblings are subjects of one level and it alone holds a single file,
  or because it is a container of subjects and a direct file is one of the container's kind only
  when a sibling subject holds a file of that kind anywhere in its subtree.

Two consequences: no rule requires a directory, so every repair merges, moves, renames or removes,
and a file placed alone in a new directory is a gap; and no rule compares one repository's subjects
with another's, so subjects, their names and number stay with each repository (DR-0011).

A declaration adds obligations. Three reduce what a rule counts; each holds only with the evidence
named here, which `status` prints, so it admits content under evidence the obligation names
(DR-0012:72) and is no repository exception (RP:11). A declaration without evidence excuses nothing.

- **(a) A record root.** Content the base tree already holds is reported and never armed (cb
  decision 1); content the candidate adds or changes meets every rule.
- **(b) A normative source.** An exact path that is a direct file of the docs home, that the docs
  registry admits as a document and that the docs reader reaches from the docs index; S4 and S5 do
  not count it.
- **(c) A received path.** The Git attribute and a source contract whose members name it.

A product root's **descriptor set** is the root's own content, not an exemption: the exact file
names recurring as direct files in two or more of its sibling subjects at one depth, each either
under that root or under a direct child of the root that holds the same names, declared once in its
`[roots.product]` entry with the consumer's own gate as evidence and printed in the map (S4, 5). The
recurrence is counted at the depth it is declared for, so an edition directory's `model.json`, which
recurs beside every edition's `guide/`, is admitted by the same declaration as the work roots'
`README.md`; an admitted name that recurs at no declared depth excuses nothing. It is I1's
declaration doing I1's work and excuses no file outside the set. An ordered series would be a fourth
reducing declaration; it ships only if the owner arms S5 (11.1).

### 4. The model

#### 4.1 Terms

- **Root**: a direct child of the repository root or of a workspace member (a directory whose
  manifest the paradigm's `[[module]]` row names and in which that module's `source_roots` apply);
  homes recur per member. A directory holding a named manifest with none of that module's source
  roots is not a member and its children are not roots; it is reported once as
  `structure_root:<path>`. A **home** is a root whose name a shared responsibility binds; a
  **product root** carries the repository's own purpose, declared with one line.
- **Subject**: a directory below a root naming one thing among its siblings. A **container** is an
  authored directory holding subjects; a **leaf** holds only files. A **package**: a directory under
  a source root of an applied module, or under the tools home, holding a direct file in a language
  of an applied module.
- **Slot**: a directory whose name is the key of a series that its layout owner fixes:
  `.config/checks/<owner>/`, `openspec/specs/<capability>/`, or a directory whose file name the
  paradigm's tool catalog fixes (`SKILL.md`), so only the directory can carry the identity.
- **Kind** (S4): the `[[language]]` or `[[formatter]]` row listing a file's suffix, and otherwise
  the suffix itself. **Unit** (S5): a direct file or a direct subdirectory. **Set-asides** (S3, S4,
  S7): the directory's index, which is its `README.md` under the docs home and elsewhere, or the
  entry document the paradigm's `[root]` table names, and the names of the paradigm's tool catalog,
  which gains the package marker and the test configuration file.

#### 4.2 Layout owners: the classes told apart before anything is counted

"Layout owner" names a class, not an owner. Each class is recognised from a declaration that exists,
and each is judged differently.

- **Protocol carrier.** The root catalog: entry documents, forge entries, `.agents`, `.config`,
  `.ethos`, `openspec`. Judged by that carrier's own obligations; no structure rule applies.
  **Archived Change**: the paradigm's `immutable_roots`, not judged and reported as its own count.
- **Record.** The profile's `record_roots`, under the evidence of 3(a): judged for its location when
  a commit adds the root (S2), never moved.
- **Normative source.** The exact paths of the profile's `normative_sources` key
  (`src/ethos/repository/profile.py:251`; RG:1550-1555), under the evidence of 3(b) (SA2).
- **Received.** Git attributes `linguist-vendored` and `linguist-generated`, under the evidence of
  3(c). A directory of only received paths is not judged, and a received path in an authored
  directory is not counted (RP:668). A marked path no source contract names is reported as
  `structure_received_unevidenced` and judged as authored (SA4, SE14), the only evidence-free mark
  this design admits. **Generated output** is untracked under `build/`; if tracked, it is received.
- **Package** (4.1). Judged by S3, S5 and S7 on the ecosystem's unit; S4 does not judge it. The
  report lists by path each package outside its module's `source_roots`, and a code file elsewhere
  makes no package: its directory is authored (SE18, SD14).
- **Authored.** Every other directory. Every rule applies.

**A shipped Skill** has one home: the slot the module naming it reads,
`src/<consumer>/skills/<name>/SKILL.md` beside its Python package, or, where the module ships the
directory as a package entry, the directory that entry names (`skills/` in `package.json`'s
`files`). Either way the module and its shipped entry name the slot, the map prints it, and S1 and
S3 excuse it (SA11, SA16).

**Each declaration has one carrier.** Profile values: the three `[roots]` values it has today, a new
`[roots.product]` (name, one-line purpose, descriptor set), and the existing `normative_sources` and
`record_roots`. Paradigm table data: each `[[module]]` row gains `languages` and `source_roots`
(`src`; `cmd`, `internal`; `packages`); the `[root]` table gains the name-bound homes, each with the
shipped reader keying on its name: `tests` (`policy/code_subjects.py:84`), `tools`
(`policy/references/carriers.py:124` and the `ethos-role=tooling` attribute), `system`
(`policy/schema.py:45`) and `evidence` (`gates/native/inputs.py:41`); the `[[parameter]]` table
gains the S5 row (SD19). `[[series]]` and a `[names]` copy of the ambiguous list are not built (11).
Only `[roots.product]` is a new value, and it answers PDC:347-357: no carrier states which root
carries a repository's own purpose, the profile owns it, and it is deleted with its directory.
Containers, subjects, packages and slots are derived, never declared per repository.

**ETHOS-created carriers** are protocol carriers, so ETHOS answers for them. Two fail the invariants
and are fixed in ETHOS (10): the docs taxonomy becomes a `.config` value, and the formation fixture
proves that a repository formed with any admitted profile has no structure gap. The gate registry
stays as the profile names it: RP:143-146 already reports `.ethos/gates.toml` as a legacy binding
file, and moving it would rewrite the sentence DR-0017:53-55 decided (SE6). **Ecosystem
conventions** are read, not excused. A Go package is one directory: its tests and platform variants
cannot move out, a one-file package is a boundary, and files beside subpackages are the parent
package's own. Whether a one-module Python package owns a boundary is ML 1.2's judgment (ML:69-75),
so S3 counts it and does not judge it (SE17).

#### 4.3 What is kept, and the rule that differs by it

- **`docs` home** (profile `roots.docs`): front matter and the document ceiling; a docs container's
  index is the Docs Registry's (PDC:468-469; `docs-registry.md:279-281`), which already blocks.
- **`rules` home**: the rule index reader. **Skills home**: the Skill registry and its gate.
  **`tests` home**: container rules, never package rules. **`tools` home**: the tools budget class
  and coverage scope. **`system` home** (PDC:324): machine contracts and the schema gate. **Record
  roots** and the root `evidence` home: location and age (S2, 3a). **Source roots** (the applied
  module: `src`; `cmd`, `internal`; `packages`): package rules.

Dropped: "plane" as a product term (the class is a fact, not a root-level kind), and declared
contract, rules, generated output and static inputs as types. `examples` and `assets` are no homes:
no rule differs by them, so S1 admits them only if declared (SE7).

### 5. The rules

Each of seven rules is decided from the tracked tree and the declarations of 3 and 4. Five apply an
invariant; S5 and S6 are prohibitions, which the owner decided (11): S5 a count, S6 not built.

**S1. The root is closed** (I1). A non-dot root directory is a home, a source root of an applied
module, a product root the profile declares as a name with a one-line purpose, or the directory a
package entry ships (the slot of a shipped Skill a module reads, which the map prints) (SA20). A
declared root the tree lacks is also a gap. A declared product root adds every rule below to that
tree, prints in `status` as part of the repository's map, and cannot switch a rule off; a one-file
product root is a gap, declared or not (S3). Repair: declare the root, or move it into a home.
Owner's choice.

**S2. One responsibility, one root** (I2). A shipped Skill's directory is a slot, not a second home:
the module that reads it and the package entry that ships it both name it, and the map prints it
once (SA20). The docs, rules and Skills homes are single profile values. A record root lies under
the docs home, the root `evidence` home or the archive: one that the base tree declares elsewhere is
reported for its location and never armed, and one a commit adds elsewhere is refused. A home's name
is reserved, so no product root is declared for a responsibility a home carries. Limit: a second
root for one responsibility under another name is a review finding, not a gap. Repair: new records
go to the one home; existing records stay (7).

**S3. A directory holds more than one thing** (I3). An authored or package directory whose subtree,
set-asides apart, is one file is a gap, unless it is a home, a slot, a one-file Go package under a
source root (the directory is the package's identity), or the only one-file subject of a container
that has no other one-file subject and at least two subjects of two or more files (SD25). A one-file
home passes because its name binds its content to that home's reader; a one-file product root or
undeclared root is a gap. One-module Python packages under a source root are counted, not decided:
whether one owns a boundary is ML 1.2's judgment. Under the tests and docs homes no package excuse
applies. Repair: merge into a sibling subject, or lift the file when the parent stays one level.

**S4. A container holds one level** (I3). An authored directory with a subject subdirectory holds,
as direct files, only its set-asides; its normative sources and the manifest of a `[[module]]` row
are not judged. A direct file is a gap only when a sibling subject holds, anywhere in its subtree
and set-asides apart, a file of the same kind, and the file is not named by a descriptor set its
product root declares; a file its product root's descriptor set names is not a gap, and refuse-new
judges the set by its name list, so a new subject of the set's shape is admitted (3, 4.2, SA19). A
direct file whose suffix no `[[formatter]]` or `[[language]]` row lists, that a sibling's own files
of that suffix cannot absorb without changing an import the ecosystem resolves from the container,
is a composition file and is not a gap; the report names it and its importer count (SA15). Packages
are not judged. Repair: place each loose file in a subject, unless S3's only-one-file-subject excuse
admits the new subject, and no repair dissolves subjects (SA3, SD18).

**S5. Width is bounded** (prohibition; owner's decision). The direct units of a directory number at
most `structure.directory_entries`: default 20, raised to at most 30 with a reason, for the whole
repository. Its one carrier is a `[[parameter]]` row, `group = "structure"`,
`key = "directory_entries"`, `unit = "entries"` (SD19). `Parameter.unit` admits four units today and
not `entries` (`contracts/paradigm/declaration.py:160`), so the Change that declares the row widens
that literal in the same diff; until then S5 has no carrier and stays a count (SD27). It reverses
ML's rule that width is never split authority, so it is put to the owner and ships as a plain count
until that decision. Report-only: over the bound, the split follows semantic owners, never a metric.

**S6. A name states a concept** (prohibition; owner's decision). No authored directory or module is
named from the paradigm's ambiguous list. It is a list rather than an invariant, and cb ships ML's
language-neutral rules as a shared gate (cb:65, 451-456), so one obligation would have two owners
(SE8). This design builds nothing for it until the owner decides (11.2).

**S7. No pass-through** (I3). A directory holding no file and exactly one subdirectory is a gap,
unless it is a root or a slot. S7 ignores set-asides and any file of zero effective lines by the
product's measure, so neither a marker nor an empty file makes a container (SD6, SD13). S7 judges
authored directories, not packages: whether a package holding only one child package is retained is
ML 1.2 item 3's decision, and the report names the case (ML:73-75, ES3).

**Not rules: a docs index and the test axis.** The Docs Registry owns the index (RG:149-155;
`docs_readme_missing`, `docs_readme_without_local_route`) and blocks on it today, so this design
adds no index rule or code; an earlier draft's stricter S8 (each subject child linked exactly once,
which ETHOS fails in both docs containers with two or more subject children) goes to that owner as a
separate proposal, measured on ETHOS first (SE16, SD11). An earlier S9 checked no test axis (SE1),
since a test tree is a container tree S1, S3, S4 and S7 already judge. The axis is a review decision
stated as a repair input, never stored, and `[roots.mirror]` is cut with it (SE7): 32 of ETHOS's 76
`tests/unit` directories sit at a source package's path.

### 6. Layouts owned by another product

Some governed repositories take a root's layout from another product: an engine that loads a
manifest naming the rest, a publishing tool's edition layout, a typesetting package. Changing such a
layout is a release of its owner, not a hand move in each consumer. A `contract` value for such a
root decided nothing or switched blocking off (SE3), so it is cut. Instead, a product root's purpose
line names the product fixing its layout, so the owner is readable and every rule still runs under
it. The report attributes nothing, reading one tree; the burn-down table marks a consumer's row as
waiting on its owner's when the owner's own report shows the same gap code at the same relative
path, and the mark changes no verdict (SE22); the owner's row precedes its consumers' (SA8).
Conformance of a consumer to a consumed layout stays with the owner's gate, which the consumer
already runs (DR-0017); ETHOS never reads another product's layout from an installed package.

### 7. Works, evidence and published paths

- **Records do not move.** No plan contains a path under a record root or an immutable root; gaps in
  content there are reported as older content and never armed (cb decision 1), while added or
  changed content is judged (3a). An accepted render is a record, declared under `record_roots`.
- **A published path is part of the product.** A path is published when it is a normative source, or
  when the latest release tag's tree holds it under the docs home or a product root. Source and test
  paths are not: the lane's proof and the class-stability check find their consumers, and a moved
  module named by a shipped provider id or an adopter profile is a breaking change with its own
  changelog entry (SE24). A plan that moves a published path marks it `published` in the preview,
  lists its consumers outside the repository by shape, and adds a changelog entry under Unreleased
  naming the old and new path. ETHOS adds no redirect.
- **Moves happen at an edition boundary.** Stock blocks a repository only from the release it binds,
  by the adopter's reviewed pin line, so a works repository takes the arming release in the lane
  preparing its next edition; every edition whose bound files move is accepted again, and the
  burn-down counts it per shape.
- **Producers move before consumers.** A burn-down row whose path another governed repository cites
  waits for its consumers' rows, or names the edit each consumer makes (SA8).

### 8. Enforcement and lifecycle

1. **Report.** The paradigm report lists structure gaps as latent gaps and leaves the verdict
   unchanged (RG:5989-5993; cb decision 1). `status` prints one line, the count per rule, the next
   action and the repository's map: homes and product roots with purposes and descriptor sets; each
   reducing declaration with its evidence and reach; the width value; the shipped Skill's slot; each
   package outside its module's source roots; and the count of one-module packages.
2. **Refuse new**, one release after the report (12.3). It takes two trees and no baseline file.
   - Bases. `pre-commit`: each parent of the commit (`HEAD`, and `MERGE_HEAD` when present), a gap
     being new only when new against every one. `land`: the merge base of the candidate and the
     accepted ref. Hosted: the event's base tree, once cb Change 4 supplies it as a `prove` input.
   - Identity. A gap's identity is its obligation and its directory. A candidate gap is stock, and
     is reported and never refused, when the base holds the same obligation's gap on the same path,
     or on a directory whose Git tree object equals the candidate's (a move with unchanged content).
     Any other gap is refused, so a commit into a mixed or chained directory, a merge, a rebase, a
     base refresh and a rename are admitted (SD1, SD2, SD10). On ETHOS one `git mv` of
     `tests/unit/adapters` carries 8 mixed containers with 87 loose files and 6 single-file
     directories, all stock by tree object.
   - Count and scope. S4 carries a count, its loose files; a stock S4 gap is refused only when that
     count exceeds the base's, and no other refusing rule has one. Only a rule an invariant decides
     can refuse: S1, S2, S3, S4 and S7. Prewrite refuses a new root S1 does not admit (RP:682). No
     refusal is raised in a release that does not ship `structure-repair`'s preview (SA17).
3. **Arm.** A named Change names the release from which stock blocks, after 0.2.0. From it S1, S2,
   S3, S4 and S7's gaps are required and prove, land and publish block (RP:682), while stock under a
   record root stays reported (3a). A repository meets the block when it binds that release; since a
   landing is judged on its candidate tree, one lane of many commits clears a repository's stock.

Paths, none of them an exemption:

- **ETHOS repairs first**, in section 10's order: its docs taxonomy Change lands before the report
  ships, and its whole tree is clean before any adopter's dated row.
- **Active adopters** repair in their own lanes while gaps are latent; the arming Change holds the
  burn-down table (shape, count, owner, bind date, producers before consumers). A repository that
  never binds the arming release is bounded only by the support window and its dated row.
- **A frozen repository's** pin does not move, so it binds no arming release and is not judged; its
  thaw lane binds the current release and leaves a clean tree. The state's owner is the Change
  defining the release soak set, a design note today, where a frozen repository records its freeze;
  this design adds no field, and the burn-down table carries each one's row with its exit (SE23).
- **The two families whose deferral the owner lifted on 2026-11-14** hold the largest stock measured
  so far. They repair in their own lanes and bind an armed release only from a lane that leaves a
  clean tree. Each family's row names the shape of its stock and the rule that clears it, or the
  Change that will; a stock beyond one lane's capacity repairs per batch boundary and the row states
  the batch count (SA18). The burn-down table is the only place stock in another governed repository
  is stated; until each family reports, the census stands in for it, restated by count there, and
  the arming Change cannot close without a dated row for each.
- **A repository without a local checkout** is read as a disposable clone by the candidate
  pre-check; one another maintainer pins meets arming only through that pin.

Gap codes, in the existing form `repository_paradigm_<obligation>:<carrier>`: `structure_root` and
`structure_home` (S1, S2), with `structure_received_unevidenced` (SA4); `structure_single_file`
(S3); `structure_mixed_level:<loose files>` (S4); `structure_width:<units>><bound>` (S5);
`structure_chain` (S7); `docs_taxonomy:<path>` for the one ETHOS carrier that moves; and a refusal
`pre_commit_structure:<obligation>:<carrier>`.

### 9. Repair

`ethos lane repair-paradigm` plans text edits per carrier and follow-ups today
(`src/ethos/repository/paradigm/repair.py:70-77`). It gains `moves`, ordered path pairs applied with
`git mv` in the Work Lane after exact-path prewrite of both ends; the preview is one patch of the
moves, the reference edits and the follow-ups.

- **Links, configuration, imports.** Relative Markdown links to and from the moved file, found by
  the existing link observer; string values equal to or starting with it in catalogued carriers
  (binding files, `.config/`, `.gitattributes`, manifests, the pipeline model); and imports, which
  ETHOS never edits: the plan names the ecosystem's rename tool as a follow-up and the lane's proof
  decides. This is the plan's weakest part.
- **Deterministic**, without input: the docs taxonomy move, and lifting a file alone in its parent.
- **Owner's choice**: every other move (the subject a file joins, the name surviving a chain, a
  root's declaration or its home, the test axis), stated as `--move <from>=<to>`, repeatable. The
  rules read only paths and declarations, so the plan evaluates them on the path set after the moves
  and refuses a move that creates a gap, naming it; refuse-new's identity admits a move of a subject
  that still holds stock, its stock staying reported (SD10). S5 stays report-only, as the size
  ceiling does (RP:702).
- **Class stability and records.** The plan evaluates every attribute and manifest glob on the path
  set before and after the moves and refuses a move changing a file's class, such as a test a later
  glob would read as tooling (SA9). No plan file is kept: an applied move is a Git rename in the
  lane's commits and the choices are tasks of the owning Change. A second run plans nothing, and a
  `--move` whose source is gone and target exists is reported as applied (SD8).

### 10. ETHOS first: every rule applied to its tree at `b10254f87`

1. **Carriers that ETHOS creates.** The docs taxonomy becomes a `.config` value in its own Change,
   the second Change after 0.2.0, after the history rebuild's second landing (12.3), with a reader
   at the old path until the last adopter binds (SD7); `docs/_meta` is an S3 gap in every docs home
   carrying it, and the gate registry does not move (SE6).
2. **Root** (S1: 1). `assets` holds the brand marks; ETHOS declares it a product root with one line
   and no descriptor set (one subject), else moves it under the docs home.
3. **Documentation** (S3: 6; S4: 1 container, 1 loose file). `docs/_meta` goes with item 1;
   `docs/concepts`, `docs/history` and `docs/plans` each join a subject; the architecture model
   lifts out of `docs/architecture/models`; one loose document in `docs/research` joins a subject.
   The generated diagram takes `linguist-generated` and a `generated` source contract whose member
   is the diagram, whose input is the model and whose gate is the architecture projection check.
   Published paths move at a release, with changelog entries.
4. **System** (S3: 1). `system/schemas/contracts` merges with its sibling schema subject. The 41
   protocol-carrier slots are unchanged.
5. **Source** (S3: 0, with 22 one-module packages counted; S7: 2; S5: 3). The packaged Skill's slot
   moves beside the package that reads it, removing two pass-through levels. `src/ethos/resources`
   and `src/ethos/resources/skills` hold no file and one subdirectory each; both collapse.
   `src/ethos/assistants` and `src/ethos/repository/registry` hold a marker and one child package
   each, so they are packages: S7 leaves them to ML 1.2's boundary finding, and each collapses only
   if that finding says so. The structure rules land in a subpackage of their own; three wide
   packages split only if the owner arms S5.
6. **Tests** (S3: 16; S4: 28 containers, 301 loose files; S7: 1; S5: 6). Single-file directories
   merge, one level collapses and 301 loose files join subjects; moves only, so no line-equivalent
   changes. The lane is sized before it starts, with a subject map for every placement; six wide
   directories split only if the owner arms S5.

### 11. What the owner decided

Two rules apply no invariant, and both change what every governed repository may do, so whether
either blocks was the owner's decision. S5's value is a count of direct units per directory, S6's
the paradigm's ambiguous-name list. The owner decided both on 2026-11-14, with 12.1's sentence.

1. **S5, width: it stays a count.** No bound is armed. The report prints the count of direct units
   per directory, and arming is decided again after the first report shows the numbers. Accepted
   with it: `[[series]]` is not built (4.2), and the parameter row and its unit ship as a count's
   carrier only (12.1). A bound reverses ML's rule that width is never split authority (ML:18,
   :26-27, :80), `rules/agents.md:68-70` and DR-0010:141-142, and the committee of 2026-10-31
   withdrew a width ceiling for that reason. A bound lets a metric be gamed by a meaningless split,
   with review the only guard; no rule in the refuse or arm set bounds a flat directory, that word
   of the request answered by this count and by review. Basis: section 2's S5 row; the default first
   came from the unpublished census, which counted direct files, so it is measured again on this
   unit before the report ships. If later armed, an ordered series becomes a fourth reducing
   declaration: a profile `[[series]]` row with a pattern, printed with its member count.
2. **S6, names: nothing is built here.** The name list is a prohibition, not an invariant, and cb
   ships ML's language-neutral rules as a shared gate, so a module's name would have two owners. The
   list and the name checks of the 2026-10-31 design (1.1) fold into cb's gate, one owner.

Not decided here: the stricter docs index (5) belongs to the Docs Registry's owner. The four items
cut in review (the contract, the mirror, the gate registry move, the two extra homes) stay cut.

### 12. Contract changes, Changes and order

#### 12.1 Contract changes

- **Product design contract.** PDC:334-337 becomes, link kept: "This is not product cloning: each
  repository keeps its domain model, the subjects, names and axes of its layout, and its provider
  shape; the ETHOS source repository paradigm fixes the shared carriers and, for the directories a
  repository authors, three invariants: each root states its meaning, each shared responsibility has
  one home, and depth expresses containment." PDC:474 names the paradigm owner beside ML. The owner
  approved the sentence on 2026-11-14; `structure-report` applies both edits with its RP delta, and
  this Change leaves the contract as it is.
- **Repository paradigm specification, MODIFIED.** RP:24 with RP:26 and scenario RP:28-31 (subjects
  stay the repository's; an undeclared `content/` root is an S1 gap); RP:33 with RP:35 (a non-dot
  root is a home, a source root or a declared product root); RP:666 with RP:668 (received needs the
  attribute and a source contract); RP:682 with RP:684 (gaps are latent until a named release; a
  commit is refused only for a new gap); RP:702 with RP:704 (a plan may hold moves; an owner's
  choice is an input, never stored); the scenario at RP:654-659 (`docs/_meta/taxonomy.toml`); and a
  `[[parameter]]` row, `group = "structure"`, `key = "directory_entries"`, `default = 20`,
  `unit = "entries"`, `bound = 30`, shipping with `structure-report-rest`, which widens
  `Parameter.unit`'s literal to admit `entries`, while S5 stays a count (S5; SD19, SD27).
- **Repository governance specification, MODIFIED.** RG:1550-1555: a normative source keeps its
  meaning as intent metadata and gains the evidence of 3(b).
- **Decision record.** DR-0027, "Common semantic structure", succeeds DR-0012:58's clause on product
  structure, test organization and documentation subject layout and DR-0012:76, and narrows
  DR-0011:42-44 and :64-67 with `docs/governance/docs-registry.md:355-358` and
  `docs/README.md:62-64`: subjects stay the repository's, and S3, S4 and S7 apply inside every docs
  home. It replaces the record the end-state design planned (1.1) and names ML:73-75 as reversed
  only if the owner arms S7 against packages, which this design does not (ES3).
- **Only if the owner arms S5.** ML:26-27 and :80, `rules/agents.md:68-70` and DR-0010:141-142.

#### 12.2 Changes and cost

Caps are line-equivalent estimates; each Change opens on its prepared patch's measured delta.

| #   | Change                  | Carries                                      | Product | Tests  |
| --- | ----------------------- | -------------------------------------------- | ------- | ------ |
| 0   | `structure-plan`        | the decision record and this design, no code | 0       | 0      |
| 1   | docs taxonomy Change    | a `.config` value; a reader at the old path  | +40     | +60    |
| 2   | `structure-report`      | S1, S3, S4, S7 latent; classes; values; map  | +450    | +480   |
| 3   | `structure-report-rest` | S2, S5's count, the row and its `unit`       | +170    | +180   |
| 4   | `structure-own-tree`    | section 10's moves; deletes no module        | 0       | 0      |
| 5   | `structure-repair`      | moves, reference edits, `--move`, stability  | +280    | +260   |
| 6   | `structure-refuse-new`  | the two-tree check                           | +120    | +150   |
| 7   | `arm-structure`         | the blocking release and the burn-down table | +20     | +40    |
|     | **Whole**               | the sum of the rows                          | +1,080  | +1,170 |

Basis: the 21 paradigm rule modules measure 82.6 product line-equivalents at the median
(`layout_invariant_code_tokens / 7.0743`), `report.py` 540.8 and `repair.py` 570.5, measured at
`b10254f87`; the seats' 97, 576 and 560 are raw physical lines, a different unit (SE27). Row 2 is
four rule bodies with classes, values, a latent channel and the map; row 3 two bodies at the median;
rows 5 to 7 keep an earlier draft's caps; row 1 is the author's estimate, and row 5 also carries a
Skill move changing a package `files` entry (SA16). These are ETHOS's figures: the title is the
fleet's, and the two families whose deferral the owner lifted hold the largest stock measured so
far, by shape and by rule, carried by their dated rows in the burn-down table rather than by any
figure here (SA21). An edition-model root's manifest and a typesetting root's composition files move
at their owners' edition boundaries, each a measured delta in the Change carrying its owner's lane.

Budgets at `b10254f87` by the shipped counter: product 80,129 of 85,000 with a review at 83,000,
tests 102,289 of 105,000, tools 8,378 of 10,000, no tools line added. By the release-candidate
plan's estimates the product ends near 82,600 and the tests near 105,600, above their ceiling, so
every test line here needs DR-0023's successor step and row 2 alone crosses the 83,000 review.

#### 12.3 Order

Changes on the paradigm's authority owner are serial with its other editors (cb decision 12).

- **Default: no code of this design lands before 0.2.0 ships.** The plan Change may land without
  code in beta.11 to beta.13. After the stable release the history rebuild's second landing is the
  first Change of the first weekly batch, as the release-candidate plan assigns it; the docs
  taxonomy Change follows, then `structure-report`, whose prerequisites are `gap-codes`,
  `record-roots-one-owner`, `fast-tier` and the first step of `status` (N1), which edit the gap
  families, the record set and `status` before it (inference from their descriptions).
- **The one exception, in two recorded acts.** By 2026-11-28 the owner records whether
  `structure-report` may target beta.13. At beta.13's landing on 2026-12-05 the rest are checked and
  it lands only if all hold: the docs taxonomy Change and the beta.13 rows its prerequisites name
  have landed, a prepared patch
  with measured budgets, the 83,000 review passed, DR-0023's successor test-budget step landed
  (12.2's rows would otherwise cross 105,000 test line-equivalents), and a recorded run on
  disposable clones of every reachable adopter, as 12.3's definition of reachable fixes it. N1 and
  `structure-report` share that batch, so a repository where N1 has not landed cannot take the
  exception. It never enters beta.14, which is frozen (SD20).
- **The rest.** `structure-report-rest` and `structure-repair` follow the report;
  `structure-own-tree` lands in lanes at batch boundaries, one slot per lane, before any adopter's
  dated row. **Reachable** means every repository a dated row of the burn-down table names, and that
  definition is what both this sentence and the beta.13 exception use. `structure-refuse-new` ships
  in the first release that also contains `structure-repair`, one release after a recorded report on
  every reachable adopter (SA12), its hosted leg after cb Change 4. `arm-structure` follows rows 4,
  5 and cb Change 2's `adopter-bump`, and carries S5 or S6 only if the owner decides them.

### 13. Approaches

DR-0027 records why three approaches were rejected: A, a closed vocabulary of planes; B, invariants
only; and C, a declared map per repository. **D is taken: invariants over layout owners, with a
closed root.** It is B plus the least of A (names only for homes a shipped reader keys on) and of C
(one new declaration, a product root's purpose, evidence on the three reducing declarations), the
smallest design that follows from invariants; its one new value passes the three questions.

## Risks / Trade-offs

### 14. Residual risks and what is not established

- **Review and names.** Review carries what the tree cannot decide: a second root for one
  responsibility under another name, the test axis, a name stating no concept, one concept under two
  names. Files that spell a shared concept in a prefix or suffix pass every rule here (1.1).
- **Flat directories.** S5 only counts. After refuse-new the first subdirectory of a flat directory
  is a new S4 gap unless every file of its kind moves with it, so a flat wide directory is the
  cheapest conforming tree until S5 is decided; this route is stated, not counted closed.
- **Gaming.** Evidence closes seven routes: one directory per file (S3 and its one excuse), a marker
  as a unit (S3, S7), one code file as a package (4.1), a loose document listed as normative (3b),
  live documentation sheltered as a record root (3a), a catch-all series (not built) and a vendored
  mark on a record tree (3c). A product root's purpose line with an unrestricted kind test would be
  a declare-anything-away switch; with the descriptor set named as the root's own content and its
  names printed in the map it is a declaration with evidence (3, S4). A single wrap admitted by S3's
  only-one-file-subject excuse stays open and is stated here, not counted closed. A synonym root
  with a purpose line stays with review; a repository that never binds has only 8's bound.
- **Repair is mostly choice.** Few moves are deterministic, and imports are left to native tools.
- **Attribution.** The product report attributes nothing; the burn-down mark rests on the owner's
  own report (6). **Cost and concentration.** About 1,080 product and 1,170 test line-equivalents,
  the sum of 12.2's rows and an estimate throughout; the tests need a budget step and the product a
  review, and one defective rule blocks every adopter at once after arming.
- **Not established:** the frozen state's tracked owner; the trees without a local checkout; any
  figure for another repository; whether every adopter's normative sources are direct files of its
  docs home; a typesetting root's composition files, which S4 admits but ETHOS does not hold, so no
  ETHOS count exercises the clause; the two-tree check's run time on the largest tree; the readers
  of the docs taxonomy path outside ETHOS; the re-acceptance counts; and three inputs that came
  after review and no seat read, none adopted here: a resource level named by an upstream
  identifier, the per-file ceiling's measure, and one authored line for format and size.
