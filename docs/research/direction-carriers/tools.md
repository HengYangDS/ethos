---
subject: ethos:research-direction-carriers-tools
role: research
state: active
relations:
  part_of: README.md
  informs: ../../decisions/dr-0011-documentation-portability.md
  constrained_by: ../../governance/product-design-contract.md
---

# Tools for Direction Carriers

Research date 2026-11-15. Review by 2027-02-15, or when OpenSpec ships a roadmap, backlog or
draft artifact, or when a text-storing tracker below reaches a 1.0 release.

Question: does a mature tool already serve as the in-repository carrier for a repository's
intake, proposals, roadmap and research, for several concurrent agent sessions and one owner?

A candidate had to meet seven constraints: (a) the data is text in the Git repository, readable
and diffable without the tool; (b) no dependence on one forge, since each repository is published
to two; (c) a command line or MCP interface that works offline and without prompts; (d) safe with
several writers in separate worktrees; (e) installable on macOS, Linux and Windows; (f) stable
releases; (g) a licence compatible with Apache-2.0 projects.

Every source is the tool's own repository, documentation or release page, read on 2026-11-15.
Nothing was installed or run, so behavior on Windows and on a self-hosted forge is unverified.

## Finding

No candidate meets all seven constraints, and none carries the four objects as plain text beside
OpenSpec. The nearest on text storage fails on concurrent writers; the nearest on concurrent
writers does not store text.

## Trackers that keep items in the repository

| Tool       | Storage                                                    | Identity                               | Several writers                                                 | Release, licence         |
| ---------- | ---------------------------------------------------------- | -------------------------------------- | --------------------------------------------------------------- | ------------------------ |
| Backlog.md | one Markdown file with front matter for each item          | sequential, found by scanning branches | duplicates stop `task list` and `search` until a repair command | 1.55.3, MIT              |
| beads      | a Dolt database in ignored directories; JSONL is an export | hash                                   | cell-level merge; the embedded mode has one writer at a time    | 1.3.4, MIT               |
| git-bug    | operations as Git objects under their own refs; no file    | hash of the first operation            | operation-based merge                                           | 0.12.0, GPL-3.0-or-later |
| beans      | one Markdown file for each item                            | prefix and four random characters      | one file for each item                                          | 0.4.2, Apache-2.0        |
| seeds      | JSONL files                                                | prefix and six hexadecimal characters  | a merge driver registered in each clone                         | 0.7.0, MIT               |
| ticket     | one Markdown file for each item                            | initials and four random characters    | one file for each item                                          | 0.3.2, MIT               |
| taskmd     | one Markdown file for each item, a published specification | sequential by default; random or ULID  | not addressed                                                   | 0.8.1, MIT               |

Sources: <https://github.com/MrLesk/Backlog.md>, <https://github.com/gastownhall/beads>,
<https://github.com/git-bug/git-bug>, <https://github.com/hmans/beans>,
<https://github.com/jayminwest/seeds>, <https://github.com/wedow/ticket>,
<https://github.com/driangle/taskmd>.

What rules each out, in the project's own words or files:

- **Backlog.md.** Two records with one identity stop its listing and search until repaired, and
  its own open task records that state is invisible across worktrees until a merge and that two
  agents can take one task. It has drafts (`draft create`, `draft promote`), milestones with a
  done-of-total count, documents and decisions, and no forge sync by its owner's decision.
- **beads.** The database directories are ignored by Git and the JSONL file is documented as an
  export that is off by default, so constraint (a) fails. Its embedded mode allows one writing
  process; several need a database server. It posts anonymous usage metrics unless switched off,
  and its `init` writes agent files unless told not to.
- **git-bug.** It adds no file to the working tree, its licence is GPL-3.0-or-later, and it has no
  1.0 release.
- **The others.** No 1.0 release; one warns that its format may change, one needs a runtime that
  the fleet does not carry, and one states collaboration as a non-feature.

## What OpenSpec offers and what its maintainers say

- A draft is derived, not stored: `openspec view` lists a Change whose tasks total zero as a draft.
  Explore writes nothing unless asked, and capture runs `openspec new change`
  (<https://github.com/Fission-AI/OpenSpec/blob/v2.0.0/docs/explore.md>).
- A request to map roadmap items to Changes is open. The lead maintainer answered on 2026-04-07
  that it is wanted in the longer term, that the missing piece is dependencies or nesting between
  Changes, that he points to an external tracker meanwhile, and that he sees the risk of becoming
  a project-management tool (<https://github.com/Fission-AI/OpenSpec/issues/889>).
- A request for a backlog was closed. The maintainers' answers: a Change that holds only a
  proposal, and the draft view. A proposal for a scratch file and one for a stored status both
  closed unmerged (<https://github.com/Fission-AI/OpenSpec/issues/429>,
  <https://github.com/Fission-AI/OpenSpec/pull/538>,
  <https://github.com/Fission-AI/OpenSpec/issues/1683>).
- Workspaces and initiatives were removed (<https://github.com/Fission-AI/OpenSpec/issues/1297>).
- No statement gives a date or a design for a roadmap, backlog or inbox artifact.

## Roadmaps and status that are derived

| Practice              | Data                                          | Derived                                                                                      |
| --------------------- | --------------------------------------------- | -------------------------------------------------------------------------------------------- |
| Rust project goals    | a metadata table in each goal's file          | markers in pages are replaced by generated tables at each build                              |
| Kubernetes            | `kep.yaml` for each proposal                  | a query writes one JSON file that the contributor site renders                               |
| Python                | the header of each PEP                        | the index is generated and validated at the documentation build                              |
| towncrier and changie | one fragment file for each change             | a build aggregates the fragments and removes them                                            |
| GSD Core              | a roadmap file and a directory for each phase | status comes from what is on disk; a ticked box has no authority, and a conflict is reported |

Sources: <https://github.com/rust-lang/goals/blob/main/src/about/goal-format.md>,
<https://github.com/kubernetes/enhancements/blob/master/hack/push-manifest.sh>,
<https://github.com/python/peps/tree/main/pep_sphinx_extensions/pep_zero_generator>,
<https://github.com/twisted/towncrier>,
<https://github.com/open-gsd/gsd-core/blob/main/docs/CLI-TOOLS.md>.

Two roadmap plugins for documentation sites render a hand-kept data file; their state is entered
by hand.

## Research and knowledge conventions

- **Open Knowledge Format 0.2** requires only a type and offers `sources` with a resource and a
  modification date, claim footnotes keyed by source, `verified` with who and when, a `status` of
  draft, stable or deprecated, and `stale_after` as an absolute instant
  (<https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/main/SPEC.md>).
- **Dated research notes bound to a commit** appear in one published practice, with the date, the
  researcher, the commit and a status in front matter
  (<https://github.com/humanlayer/advanced-context-engineering-for-coding-agents/blob/main/ace-fca.md>).
- **Agent memory** is vendor-specific and partly outside the repository: one assistant keeps its
  automatic memory under the user's home directory, shared across worktrees and not across
  machines (<https://code.claude.com/docs/en/memory>). `AGENTS.md` and `llms.txt` define no date,
  source or owner field (<https://agents.md/>, <https://llmstxt.org/>).
- **Decision-record tools** had no release since 2024 and 2018.

## What this study takes from the tools

- One file for each item, so two writers conflict only on the same item.
- An identity that two branches cannot both allocate: a date with a slug or random characters,
  never the next number.
- A roadmap whose state is read from the tree, where a mark written by hand has no authority.
- A review instant on a research record, as the knowledge format's `stale_after`.
- OpenSpec's own draft, a Change without tasks, as a native carrier for a proposal.

## Not verified

- Any tool's behavior on Windows, and pushing a database's refs to a self-hosted forge.
- One tool's storage format and two tools' file formats were not read.
- Two pages opened with instructions addressed to an agent; they were not followed.
