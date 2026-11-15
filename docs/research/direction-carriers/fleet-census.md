---
subject: ethos:research-direction-carriers-fleet-census
role: research
state: active
relations:
  part_of: README.md
  informs: ../../decisions/dr-0011-documentation-portability.md
  constrained_by: ../../governance/product-design-contract.md
---

# Fleet Census of Direction and Documentation Carriers

Research date 2026-11-15. Review by 2027-02-15, or when a governed repository joins or leaves.

Question: where do ETHOS and the repositories it governs keep their end state, roadmap, ideas,
designs and research, and how alike are their documentation homes?

## Method

Read-only, from Git objects. For ETHOS, the tree of `dev` at `c79f3aaf8`. For the fleet, the tree of
`dev` in each of the 14 governed checkouts on the releasing host: the first-level directories of the
documentation home, the documents whose path names a plan-like carrier, the decision and research
holdings, and whether a document's front matter declares a role. Governed repositories appear by
shape and count. Three governed repositories exist only on a forge; a later section holds what was
read of them. The content of the plan documents was not read. This census read no forge issue
tracker; the fleet seat's reading of open issues is in a later section.

## ETHOS

| Measure                                                          | Value      |
| ---------------------------------------------------------------- | ---------- |
| Documents under `docs/plans`                                     | 1          |
| Nonblank lines of that plan, against the bound                   | 500 of 500 |
| Nonblank lines of the product design contract, against the bound | 500 of 500 |
| Archived Changes                                                 | 353        |
| Archived Changes with a `Workflow follow-up` section             | 152        |
| Follow-up bullets in those sections                              | 248        |
| Tasks withdrawn under DR-0016                                    | 96         |
| Archived Changes that change no requirement (`skip_specs: true`) | 174        |
| Documents in the state `planned` or `experimental`               | 0 of 68    |
| Research documents                                               | 12         |

- The specification requires exactly two design authorities and forbids a parallel roadmap; the
  plan forbids an active backlog and a feedback registry.
- The 43 rows of the release-candidate gate are prose in DR-0026 and in an archived design. No
  tracked file lists them as data.
- The installed OpenSpec 2.0.0 has four artifacts for a Change and no artifact for exploration, a
  roadmap or a backlog.
- Outside the tree on the day of the census: one session's notes with 38 sections of defects,
  rulings and proposals, 94 design documents in ignored work directories, and 75 files of agent
  memory. These are inferences about use: nothing in the tree says who reads them.

## The fleet

Nine of the 14 repositories have a documentation home. The five without one hold content or media
and no product documentation.

| First-level name                                                                          | Repositories |
| ----------------------------------------------------------------------------------------- | ------------ |
| `decisions`                                                                               | 7            |
| `architecture`                                                                            | 5            |
| `governance`, `reference`                                                                 | 4 each       |
| `guides`, `operations`, `evidence`, `history`                                             | 3 each       |
| `concepts`, `research`, `plans`, `_meta`                                                  | 2 each       |
| `experience`, `current`, `future`, `_generated`, `planning`, `portal`, `studies`, `start` | 1 each       |

| Object                | Forms found          | Repositories without one |
| --------------------- | -------------------- | ------------------------ |
| Roadmap or plan       | 4 live and 1 retired | 10                       |
| Contract or end state | 4                    | 10                       |
| Research              | 2                    | 11                       |

- The plan forms: a `plans` directory with one document (two repositories), a `future` directory,
  a task ledger kept by a backlog tool in a dot directory (22 open tasks, 64 completed, with
  drafts, decisions and milestones), and one roadmap document at the home's root. The retired
  form is a `planning` directory whose 37 documents lie under `archive` beside one index.
- The contract forms: a product design contract under `governance`, a product contract and a
  charter at the home's root, and a numbered blueprint under `operations` that mixes architecture
  with a program of work. An experience page that an earlier count took for a contract declares
  the role `explanation`.
- Research is a `research` directory in two repositories and a `studies` directory in one. That
  repository also keeps a research lifecycle with five states and a dossier template.
- Role metadata is complete in seven of the nine homes and absent in two, which hold 255 and 247
  documents. One of the two is a Sphinx home, with its configuration and index at the root and
  generated reference pages, so Markdown front matter is not its toolchain's form.
- Directories that carry no role: `evidence` in three homes (7, 3 and 135 files), a taxonomy
  directory in three, generated views in one, a state named `current` in one (66 files), an asset
  directory in one and a landing page's directory in one.

## Repositories that only a forge holds

Read on 2026-11-15 by the fleet seat of the design's review, names only. One keeps 16 documents
flat at the root of its documentation home (a design philosophy, plans, runbooks, a release
process, task logs), one keeps seven flat documents, and one keeps a single document. None has a
first-level directory. Two of them have another maintainer.

## Where intent is kept today

- Ignored work directories of the sessions that own each repository: 58 directories with 66
  Markdown files in one repository, 14 with 69 in another, 10 with 9 in a third, measured two
  levels deep. ETHOS's own are above.
- Agent memory, outside every repository.
- One tracked backlog tool, in one repository.
- No forge issue: 0 open issues in the four repositories whose issues could be read.

## What a move of a first-level name costs

Counted by the fleet seat on 2026-11-15: mentions of the directory outside archived Changes, and
relative links from inside the documentation home.

| Shape                                              | Files | Mentions | Of them in code and configuration | Relative links |
| -------------------------------------------------- | ----- | -------- | --------------------------------- | -------------- |
| ETHOS, three directories; three packaged documents | 7     | 49       | 22                                | 49             |
| A guidance repository, one directory               | 4     | 3        | 0                                 | 4              |
| Three product repositories, three or four each     | 25    | 47       | 13                                | 20             |
| A repository under repair, seven directories       | 131   | 399      | 270                               | 77             |
| A repository under repair, three directories       | 216   | 316      | 89                                | 158            |

No governed repository ships a documentation path in a package; ETHOS ships three. Links that pin
a revision do not break.

## Limits

- A name was counted by its spelling; two repositories may use one name for different content.
- The census reads one host. The three repositories that only a forge holds may differ.
- "No roadmap" means no document whose path says so; a repository may keep one in a forge.
- The counts of forms were corrected on 2026-11-15 after the fleet seat's review: an earlier
  reading counted five contract forms and eight repositories without one.
