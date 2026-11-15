---
subject: ethos:research-direction-carriers-practice
role: research
state: active
relations:
  part_of: README.md
  informs: ../../decisions/dr-0011-documentation-portability.md
  constrained_by: ../../governance/product-design-contract.md
---

# Practice in Primary Sources

Research date 2026-11-15. Review by 2027-05-15, or when OpenSpec adds an artifact for a roadmap,
a backlog or exploration.

Question: how do mature projects and methods keep proposals, roadmaps, idea intake, decision
records, documentation structure and research, and what do spec-driven agent workflows add?

Every source below is the project's or the method's own page, read on 2026-11-15. The findings
report what the sources say. The two sections after them are this study's reading.

## Proposals

| Process    | Carrier and identity                                    | States for "not now"           | Acceptance and execution                                        |
| ---------- | ------------------------------------------------------- | ------------------------------ | --------------------------------------------------------------- |
| Rust RFC   | `text/NNNN-name.md`; the number of its pull request     | `postponed`                    | a tracking issue; acceptance says nothing of priority           |
| Python PEP | `pep-NNNN.rst`; next free number                        | `Deferred`, `Provisional`      | `Final` when the code is merged; `Superseded-By` and `Replaces` |
| Kubernetes | `keps/sig/NNNN-slug/` with `kep.yaml`; the issue number | `deferred`, `provisional`      | `implementable`, then a release milestone chosen apart          |
| Go         | an issue, then `design/NNNN-name.md`                    | `Hold`                         | `Proposal-Accepted`, then a work milestone; the issue tracks it |
| OTEP       | `oteps/NNNN-slug.md`; the number of its pull request    | none                           | `approved`, then `integrated` by a specification change         |
| Django DEP | one directory for each state; number given at merge     | none; deferred means withdrawn | `Final` when merged into the main repository                    |

Sources: <https://raw.githubusercontent.com/rust-lang/rfcs/master/README.md>,
<https://peps.python.org/pep-0001/>,
<https://raw.githubusercontent.com/kubernetes/enhancements/master/keps/sig-architecture/0000-kep-process/README.md>,
<https://raw.githubusercontent.com/golang/proposal/master/README.md>,
<https://raw.githubusercontent.com/open-telemetry/opentelemetry-specification/main/oteps/README.md>,
<https://raw.githubusercontent.com/django/deps/main/final/0001-dep-process.rst>.

The templates share fixed sections for evidence: Rust has `Prior art`, `Rationale and
alternatives`, `Unresolved questions` and `Future possibilities`; the KEP template has
`Alternatives`, `Non-Goals` and a dated `Implementation History`; Go's design template has
`Rationale` and `Open issues`
(<https://raw.githubusercontent.com/rust-lang/rfcs/master/0000-template.md>,
<https://raw.githubusercontent.com/kubernetes/enhancements/master/keps/NNNN-kep-template/README.md>,
<https://raw.githubusercontent.com/golang/proposal/master/design/TEMPLATE.md>).

## Roadmaps

| Project            | Carrier                                                 | An entry                                                   |
| ------------------ | ------------------------------------------------------- | ---------------------------------------------------------- |
| GitHub roadmap     | issues on a board, by quarter and an exploratory column | a phase label; `shipped` closes it with a changelog link   |
| Rust project goals | one file for each goal by year; site tables generated   | a metadata table, work items, a tracking issue             |
| Kubernetes release | issues and one board for each release                   | stage, milestone, tracked or deferred, freeze dates        |
| TypeScript         | a wiki page and one iteration issue for each release    | a schedule and items that link to issues                   |
| VS Code            | a wiki roadmap and a monthly iteration issue            | a checkbox, an issue reference, owners, a deferred section |
| containerd         | a `ROADMAP.md` that holds no list                       | issues say what, milestones say when                       |
| Backstage          | `docs/overview/roadmap.md`, a half-year edition         | prose for each initiative                                  |
| Prometheus         | a site page                                             | a few sentences, no link to tracked work                   |

Sources: <https://raw.githubusercontent.com/github/roadmap/main/README.md>,
<https://goals.rust-lang.org/how_to/propose_a_goal.html>,
<https://raw.githubusercontent.com/kubernetes/sig-release/master/release-team/role-handbooks/enhancements/README.md>,
<https://github.com/microsoft/TypeScript/wiki/Roadmap>,
<https://github.com/microsoft/vscode/wiki/Iteration-Plans>,
<https://raw.githubusercontent.com/containerd/containerd/main/ROADMAP.md>,
<https://raw.githubusercontent.com/backstage/backstage/master/docs/overview/roadmap.md>,
<https://prometheus.io/docs/introduction/roadmap/>.

containerd gives its reason in the file: roadmap files "quickly become out of date".

## Intake

| Practice        | Carrier                                                     | Rule                                                       |
| --------------- | ----------------------------------------------------------- | ---------------------------------------------------------- |
| Shape Up        | none: "No backlogs"                                         | a pitch is bet on at the betting table or let go           |
| Django          | issues of a separate repository for new features            | a feature needs a DEP to go further                        |
| Go              | an issue with the `Proposal` label                          | a weekly review group moves it between named columns       |
| GitHub guidance | Discussions for open ideas, Issues for specific work        | discussions "often do not result in an actionable task"    |
| Backlog.md tool | a `backlog` directory: tasks, drafts, milestones, decisions | drafts are promoted to tasks; an archive keeps identifiers |

Sources: <https://basecamp.com/shapeup/2.1-chapter-07>, <https://github.com/django/new-features>,
<https://docs.github.com/en/get-started/using-github/communicating-on-github>,
<https://raw.githubusercontent.com/MrLesk/Backlog.md/main/CLI-INSTRUCTIONS.md>.

## Decisions, documentation structure and research

- **Decision records.** Nygard's record has a title, context, decision, status and consequences,
  is numbered once, and is kept and marked when superseded
  (<https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions>). MADR 4.0.0 keeps
  records under `docs/decisions` with a status such as `superseded by ADR-0123`
  (<https://adr.github.io/madr/>).
- **Documentation structure.** Diátaxis names four kinds (tutorials, how-to guides, reference,
  explanation), calls itself "a guide, not a plan" and says not to create empty structures. Its
  pages say nothing about plans, roadmaps or research (<https://diataxis.fr/>). arc42 has twelve
  sections, the ninth for decisions, and none for a roadmap (<https://arc42.org/overview>).
- **Design documents.** The public account of design documents at Google lists context and scope,
  goals and non-goals, the design, alternatives considered and cross-cutting concerns, and treats
  later changes as new documents beside the old
  (<https://www.industrialempathy.com/posts/design-docs-at-google/>).
- **Freshness.** The same company's book describes an owner and a reviewed date on a document
  and a reminder when it goes untouched (<https://abseil.io/resources/swe-book/html/ch10.html>).

## Spec-driven agent workflows

| Workflow        | Standing documents                         | For each change                               | Roadmap or backlog artifact                                                      |
| --------------- | ------------------------------------------ | --------------------------------------------- | -------------------------------------------------------------------------------- |
| OpenSpec 2.0.0  | `openspec/specs`                           | proposal, delta specs, design, tasks; archive | none; explore writes nothing unless asked                                        |
| GitHub Spec Kit | a constitution under `.specify/memory`     | spec, plan, research, tasks under `specs`     | none in the core; an extension adds an assessment with a `go` or `kill` decision |
| Kiro            | product, technology and structure steering | requirements, design, tasks                   | none                                                                             |
| BMAD            | briefs, requirement and architecture files | an epic's ordered tickets                     | none; the backlog is not owned by the build step                                 |

Sources: <https://raw.githubusercontent.com/Fission-AI/OpenSpec/main/docs-lab/guides/explore.md>,
<https://raw.githubusercontent.com/github/spec-kit/main/spec-driven.md>,
<https://raw.githubusercontent.com/github/spec-kit/main/extensions/assess/README.md>,
<https://kiro.dev/docs/specs/>,
<https://raw.githubusercontent.com/bmad-code-org/BMAD-METHOD/main/README.md>.

## Patterns that at least three sources share

- One design document for each proposal, with an identity taken from outside the text.
- A state for "not now" that is not a rejection.
- Acceptance does not schedule the work.
- The design document is a record; execution is tracked by another object.
- A roadmap that must stay current is kept as tracked objects or generated, and a roadmap entry is
  a thin pointer to one.
- Intake is kept apart from tracked work.
- Evidence and alternatives sit inside the proposal under fixed headings.
- An owner and a review date control staleness.

## Where the sources disagree

- **A roadmap in the repository or in the forge.** Files and pages in four projects; forge objects
  in four, one of them with an explicit reason against a file.
- **A backlog or none.** Shape Up keeps none. The proposal processes, the backlog tool and the
  release boards keep a holding place with identities.
- **How a record is superseded.** A status on the old record, a status that names the new one, or
  a pair of headers.
- **Structure designed first or grown.** Diátaxis grows it; every proposal process prescribes it.

## Not reached

- The Diátaxis page on complex hierarchies returned 404.
- No page on spikes of Extreme Programming could be read (certificate mismatch), so nothing here
  rests on it.
- No primary source states a validity limit for a research record beyond the freshness date.
- The backlog tool publishes no schema for its front matter; its own files and its instructions
  disagree on the file-name prefix.
