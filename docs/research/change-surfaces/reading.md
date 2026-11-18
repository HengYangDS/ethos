---
subject: ethos:research-change-surfaces-reading
role: research
state: active
relations:
  part_of: README.md
  constrained_by: ../../governance/product-design-contract.md
---

# Reading: What a Change's Surfaces Are For

Research date 2026-11-18. Review by 2027-05-18, or when the design that this reading informs is
accepted or refused.

Question: what do the three studies of this topic say together, where does ETHOS stand against
them, and what follows?

This page is the study's reading. Its findings are in [Branch names](branch-names.md),
[Issue and change templates](issue-and-change-templates.md) and [Peers](peers.md); what it says
of ETHOS was read in the lane of 0.2.0-beta.11 at `43194202c` on 2026-11-18, each fact with its
file. It decides nothing: a change of a fixed name or of a template is a Change with its own
design and review.

## One model for the three surfaces

A change meets its readers at a boundary of trust, and three questions are asked there. Each
surface answers one of them.

| Question at the boundary                    | Surface                                  | What a good answer is                                   |
| ------------------------------------------- | ---------------------------------------- | ------------------------------------------------------- |
| Where may this go, and who may move it?     | the name of the branch                   | a role that rules can match                             |
| What is claimed, and can a reader check it? | the issue form; the change's description | a claim with the facts that make it checkable           |
| Who answers for it?                         | the marks of authorship                  | a person who can be held to it, and a record of the way |

## Five principles that the sources support

1. **A field is worth what it costs to fake.** A coding agent fills any field, ticks any box
   and writes any description for nothing. The kernel withdrew a tag that it had asked authors
   to declare; the GitHub CLI's template says that test results "do not belong here" because a
   reviewer sees them in CI; uv's template has no checkbox. What a tool can compute is a check,
   and what a runtime knows is a record; neither is a declaration.
2. **Every surface has two readers, a person and an agent.** GitHub tells its users to "think
   of the issue you assign to Copilot as a prompt"; five of nineteen repositories let a workflow
   read incoming issues first; thirteen use typed forms. Structure is for the second reader.
3. **What is scarce is a person's attention and a person's answer.** The kernel keeps one rule
   through every revision: only a human certifies. The GitHub CLI asks who replies to review;
   OpenHands keeps a part that an agent may not write; Spec Kit caps open changes for one
   account. A surface must carry what only the person can say.
4. **One fact has one owner, and a surface is a projection of it.** A branch name that says
   `feat/` beside a commit that says `feat:`, or a checkbox that says "tests pass" beside a CI
   run, is a second copy that nothing keeps true. Conventional Branch 1.1.0 needed a second set
   of prefixes for agents because one string cannot carry two facts.
5. **A prefix is a boundary.** A forge's rules match names by pattern; GitHub's agent "can only
   push to" its `copilot/` branch. What a rule must match belongs in the name, and nothing else
   needs to be there.

## ETHOS against the principles

| Surface                 | ETHOS today                                                                                                                                                       | Read in                                                                                       | Against the principles                                                  |
| ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| Branch names            | five fixed role names: `main`, `dev`, `candidate/dev`, `work/`, `proposal/`; no repository may differ                                                             | `contracts/paradigm/paradigm.toml` `[branch]`; DR-0012                                        | holds 4 and 5: a name is a role; the kind of change stays in the commit |
| The review ref          | `proposal/<slug>`, derived from the lane; hosted CI runs on `proposal/**`; `dev` and `main` are protected                                                         | `contracts/branch/roles.py`; `.config/ci/verification.cue`                                    | holds 5; the word differs from every convention read                    |
| The contract's sentence | "adopters may rename refs but preserve the roles"                                                                                                                 | `product-design-contract.md` 263                                                              | contradicts the accepted requirement, which fixes the names             |
| A maintained release    | a signed tag cut from a lane on "a historical accepted base"; no named line                                                                                       | `docs/reference/integration-and-release.md` 85-91                                             | the path of tags; whether it was ever exercised was not read            |
| Issue intake            | one Markdown template in ETHOS's own terms (Subject, Intent, Contract, Acceptance, Evidence); blank issues open                                                   | `.github/ISSUE_TEMPLATE/task.md`                                                              | misses 2: no form, no kind, no version, no command output               |
| The change description  | Summary; five checkboxes of commands; three of governance; the same text for both forges                                                                          | `.github/PULL_REQUEST_TEMPLATE.md`                                                            | breaks 1 and 4: it asks the author to assert what ETHOS proves          |
| The first checkbox      | `nox -s tests`                                                                                                                                                    | `nox -l` in the lane lists 31 sessions; none is `tests`; `215af814b` of 2026-11-01 removed it | names a command that the product removed                                |
| What checks the files   | that the named sections exist                                                                                                                                     | `.config/checks/ci-projection/policy.toml` `[[forge_surface]]`                                | a check of headings, not of content                                     |
| Authorship              | commits are signed by a person; an executor names itself (`--actor`, `ETHOS_ACTOR`); a lane's lease has a holder                                                  | `adapters/actor.py`; glossary, Lease                                                          | holds 3; the record of 1 exists and reaches no reader of a change       |
| The fleet               | of ETHOS and 13 local governed repositories, 3 hold any issue or change template: ETHOS 4 files, architecture-publisher 9 (with forms and a chooser), di-effect 2 | a count over each repository's `dev`, 2026-11-18                                              | no shared surface: each repository is alone                             |

The templates date from 2026-06-30 to 2026-08-06 by their history, before the proof, the
receipts and the fixed names of today.

## What follows for the names

There is no standard to conform to, and the family that the question names (`release/*`,
`hotfix/*`, `feat/*`) answers other questions than ETHOS's names do: the kind of a change, and
the stage of a release with long-lived release branches. ETHOS's names say which role a ref
plays on the way to acceptance. `proposal/*` is the head that is offered for review and is no
one's place to write; where a server keeps review, that role has a name of its own (Gerrit's
`refs/for`), and where an agent writes, its one writable prefix is the same kind of boundary.

| Option                                                            | What it costs                                                                                                                           | What it gives                                                           |
| ----------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| A. Keep the five names; say in one place what each corresponds to | a table in the reference; the contract's sentence brought to the requirement                                                            | no migration; a reader from Git Flow or GitHub flow finds his word      |
| B. Rename `proposal/` to a word of review (`review/`)             | 139 lines in 49 tracked files of ETHOS; every governed repository's refs, rules and CI triggers; a compatibility reader for one release | ends the two meanings of "proposal" (a Change's document, a ref)        |
| C. Publish lanes under typed names (`feat/`, `fix/`)              | a lane carries many Changes of several kinds (the release lane archived 14), so a type is false for most lanes                          | the look of the common family                                           |
| D. Add a named line for a maintained release (`release/<x.y>`)    | a sixth role and its protection; a rule for the direction of fixes                                                                      | the one member of the family that names something ETHOS has no name for |

This reading's order: A now; D decided before the first patch release of 0.2, on the evidence
of one exercised maintenance release; B only together with another forced migration of every
repository; C not at all.

The criterion behind that order (a name carries its role and what a rule must match) is this
reading's induction from the sources, and ETHOS's five names were measured with it by the same
reader. It also admits what ETHOS does not have: a prefix for an agent's branches is sound
where a forge's rule must match them, and ETHOS needs none only because the signer and the
actor already record who wrote.

## What follows for the templates

For ETHOS the facts that a change description holds already have owners: the intent is the
OpenSpec Change, the content is the commits, the verification is the proof and its receipt, the
author is the signer and the executor is the actor. By principle 4 the description is a
projection: written by the command that publishes the review ref, from those owners, in fixed
sections, with one part left for the person.

| Part of the description                          | Owner it is projected from                 | Today                                     |
| ------------------------------------------------ | ------------------------------------------ | ----------------------------------------- |
| What changes and why                             | the Change's proposal, by link and summary | typed by hand under "Summary"             |
| The commits                                      | the introduced range                       | absent                                    |
| How it was verified                              | the proof's verdict, its gates, its digest | five checkboxes, one of a missing command |
| Who and how                                      | the signer; the actor; the lease's holder  | absent                                    |
| What a reviewer should doubt; who answers review | the person                                 | absent                                    |

Intake is the opposite case: the reporter holds the facts and ETHOS holds none, so a typed form
is the right carrier, and the product can fill most of it. Every refusal of ETHOS already has a
code, a request and a next step in a structured answer; a command that turns one refusal into
a prefilled report, redacted by the product's own redaction, is what OpenSpec's
`openspec feedback` does for its users.

## Mechanisms worth taking, in this reading's order

| Mechanism                                                                        | Seen in                                                  | Fit                                                                | Size               |
| -------------------------------------------------------------------------------- | -------------------------------------------------------- | ------------------------------------------------------------------ | ------------------ |
| Correct the description's checkboxes to what exists, or remove them              | uv, GitHub CLI                                           | repairs a false instruction                                        | one file           |
| A chooser configuration: no blank issue; security and questions by link          | 10 and 11 of 19                                          | closes the open door before the first outside report               | one file           |
| Forms for a defect, a feature and documentation, with version and command output | OpenSpec, Claude Code, Codex                             | principle 2                                                        | three files        |
| The contract's sentence on renaming brought to the requirement                   | -                                                        | ends a contradiction between two owners                            | one line           |
| The description generated at publication                                         | GitLab's variables; no peer generates it whole           | principle 4; the product's own claim of proof-carrying change      | product code       |
| The executor recorded in the proof and shown in the description                  | Spec Kit declares it; the kernel withdrew a declared tag | principle 1: a record, not a declaration                           | product code       |
| A report filed by the product from a refusal                                     | OpenSpec                                                 | principle 2; the refusal already holds the facts                   | product code       |
| A Change tied to the issue it serves, and a proposal reviewed before its code    | OpenSpec, gsd-core                                       | ETHOS admits work before it is written; the forge shows none of it | a field and a rule |
| A reader that judges the description's content                                   | maintainer-contracts, OpenHands                          | replaces the check of headings                                     | tool code          |
| A stated policy for contributions made with agents                               | Ghostty, Zed, Astral, Kubernetes                         | a product for stewardship by people and agents states none         | one section        |
| Shared surfaces for the governed repositories                                    | one governed repository has its own                      | 11 of 13 have none; DR-0012 lists the CI model, not these files    | a paradigm row     |
| Triage and duplicate detection by a workflow                                     | 5 and 4 of 19                                            | no volume yet: 0 stars, no outside issue                           | later              |

## What this reading does not decide

- Whether an agent's part in a change is shown to the public. The sources disagree, and it is
  a choice of the owner's, not of evidence.
- Which release carries which mechanism. The head of 0.2.0-beta.11 is frozen, and the order of
  the batches is the committee's.
- The design of any mechanism above. Each is a Change with its own decisions.

## Not verified

- Whether a maintenance release by tag was ever exercised in a governed repository.
- The cost of option B outside ETHOS's own tree: the governed repositories' rules and triggers
  were not counted.
- Whether GitHub accepts a description supplied at publication in every path that ETHOS uses;
  ETHOS publishes refs today and opens no request on a forge.
- The count of sessions is the lane's own `nox -l`; the three counts of principle 2 are the
  peer study's script.
