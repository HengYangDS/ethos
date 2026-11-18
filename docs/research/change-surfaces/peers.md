---
subject: ethos:research-change-surfaces-peers
role: research
state: active
relations:
  part_of: README.md
  constrained_by: ../../governance/product-design-contract.md
---

# Peers: Mechanisms in Nineteen Repositories

Research date 2026-11-18. Review by 2027-05-18, or when a repository of the first group below
publishes a release that changes its contribution process.

Question: which mechanisms for intake, change, authorship and triage do repositories positioned
like ETHOS, and well-run projects that coding agents write in, keep on GitHub?

The repositories were chosen from GitHub's own search under ETHOS's topics (`openspec`,
`repository-governance`, `agentic-workflows`, `coding-agents`) and the neighbouring
`spec-driven-development`, by stars, on 2026-11-18. For each, the files of the default branch
under `.github/`, `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md` and the names of its workflows
were read through the forge's API. The findings report what those files say. The two sections
after them are this study's reading.

## The repositories

| Group                                        | Repositories (stars on 2026-11-18)                                                                                                                                                       |
| -------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Spec-driven work with agents                 | Spec Kit (150,328), OpenSpec (75,110), BMAD-METHOD (55,492), gsd-core (11,652), cc-sdd (3,771), qualitylayer (2,151)                                                                     |
| Under the topic `repository-governance`      | CoaseEdge repo-governance (2), Evagix (1), maintainer-contracts (1)                                                                                                                      |
| Coding agents and tools that agents write in | Claude Code (156,065), Codex (135,695), Kubernetes (129,348), Gemini CLI (108,913), Zed (95,245), OpenHands (93,703), uv (92,201), Ghostty (64,200), goose (56,738), GitHub CLI (47,068) |

The largest repository under the topic `repository-governance` has three stars. ETHOS's own
position, a repository's rules for change enforced for people and agents alike, has no large
peer on GitHub under that name; its neighbours are the spec-driven tools.

## Intake and admission of work

| Mechanism                                                  | Where                         | What the files say                                                                                               |
| ---------------------------------------------------------- | ----------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| Every change starts at an issue, approved by a label       | OpenSpec, gsd-core, OpenHands | `approved`; `approved-enhancement`, `approved-feature`; `ready-for-dev` "means it has clear acceptance criteria" |
| Changes are opened by maintainers and invited contributors | OpenSpec                      | "Opening pull requests is limited to maintainers, so wait for an invitation on the issue"                        |
| A feature is two changes: its proposal, then its code      | OpenSpec                      | "**Proposal:** only `openspec/changes/<name>/`" then "**Implementation:** after the proposal merges"             |
| The tool files its own report                              | OpenSpec                      | "`openspec feedback \"what happened\"` files a bug for you with your version and platform filled in"             |
| A different bar for each kind of contribution              | gsd-core                      | fix, enhancement and feature each have a form, a template and "a different bar for acceptance"                   |
| A cap on open changes for one account                      | Spec Kit                      | "three open PRs"; a fourth "may receive lower review priority"                                                   |
| A scored review                                            | Spec Kit                      | seven dimensions, 0 to 2 each, among them "Real-world evidence", "Scope discipline", "Test evidence"             |
| No unfinished change                                       | gsd-core                      | "draft PRs are automatically closed"                                                                             |

## The change as a checked contract

| Mechanism                                            | Where                     | What the files say                                                                                                                     |
| ---------------------------------------------------- | ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| The description is parsed and judged                 | maintainer-contracts      | "required sections with minimum meaningful content", "forbidden template placeholders", "required body patterns such as linked issues" |
| Evidence asked for by the paths changed              | maintainer-contracts      | "review evidence to scale with the risk of a change"                                                                                   |
| A task's paths and scope are a budget                | CoaseEdge repo-governance | RG008: a Task Contract's path and scope budget, with a report of drift; RG009: budgets by kind of change                               |
| A waiver is bound to what it waives                  | CoaseEdge repo-governance | RG005: bound to the allowed approver, the current head of the request and the governed diff                                            |
| Tests belong to one tier                             | CoaseEdge repo-governance | RG002: `pr-blocking`, `nightly` or `manual-smoke`, and one alone                                                                       |
| A part of the description is the human's alone       | OpenHands                 | a validator fails a change whose `HUMAN:` part is missing or empty                                                                     |
| The title and the target are corrected by a workflow | gsd-core                  | `pr-title-validator`, a validator of the target branch, `changeset-required`                                                           |
| One hard rule engine behind every caller             | CoaseEdge repo-governance | agents' skills "call the locked CLI"; "they do not reimplement the hard rules, and cannot override" a decision                         |

CoaseEdge's README states the limit of such rules itself: they "report only the facts that the
repository has declared" and cannot prove that a change is right.

## Agents as readers, writers and triagers

Counts are of the nineteen, by the workflow names and the files read.

| Mechanism                                                   | Count | Where                                                                          |
| ----------------------------------------------------------- | ----- | ------------------------------------------------------------------------------ |
| Instructions for agents at the root                         | 14    | from 15 lines (maintainer-contracts) to 190 (Zed)                              |
| Triage of issues by a workflow, most by an agent            | 5     | Claude Code, Gemini CLI, GitHub CLI, Zed, uv                                   |
| Detection of duplicates                                     | 4     | Claude Code, OpenHands, Zed (it also tracks the bot's hit rate), gsd-core      |
| Workflows written as Markdown and compiled to a locked file | 2     | GitHub CLI (`issue-triage.md`), Spec Kit (`bug-assess`, `pr-assess`)           |
| A file that tells the forge's reviewing agent what to skip  | 1     | goose (`.github/copilot-instructions.md`: "Skip These", "When to Stay Silent") |
| Steps that prepare the agent's environment                  | 1     | GitHub CLI (`copilot-setup-steps.yml`)                                         |
| Closing of stale items                                      | 6     | goose, Spec Kit, cc-sdd, gsd-core, Codex, Zed                                  |

Kubernetes's `AGENTS.md` is 39 lines: how to speak, four constraints, the contributor's duties,
the commands, the style. It tells an agent to "remind the human author that they are responsible
for all submitted changes".

## Community and supply files

| File or setting                  | Count | Note                                                                |
| -------------------------------- | ----- | ------------------------------------------------------------------- |
| A security policy                | 13    |                                                                     |
| Discussions                      | 11    | the chooser sends questions there                                   |
| Dependabot                       | 10    | Renovate in one (uv)                                                |
| CODEOWNERS                       | 9     |                                                                     |
| CodeQL                           | 3     |                                                                     |
| Changesets required for a change | 2     | OpenSpec, gsd-core; a release tool's config in one more (OpenHands) |

## Patterns that at least three sources share

- Work is admitted at the issue, by a named label, before code is written; the change then
  links the issue it serves.
- What a rule can decide is decided by a workflow or a tool (the title, the target, the linked
  issue, the changelog entry), and the template keeps what a tool cannot know.
- Agents read one root file, and agents do the first reading of incoming issues.
- The projects that agents write in most have closed the open door: forms alone, no blank
  issue, and a limit, a label or an invitation before a change is opened.

## Where the sources disagree

- **Open or invited.** OpenSpec limits who opens a change; Kubernetes and uv take one from
  anyone and ask for a disclosure or a policy to be read.
- **Draft or finished.** GitHub's own agent opens drafts for a human to finish; gsd-core closes
  drafts.
- **Rules in the forge or in the repository.** gsd-core, Gemini CLI and Zed run dozens of
  workflows (34, 47, 46); the three small governance tools put the rules in a local engine that
  the forge calls.

## Not reached

- Each repository was read at one commit of its default branch; no history of how a file came
  to be was read, so nothing here says which mechanism worked.
- GitLab was not searched: every repository here lives on GitHub.
- Private or enterprise practice is not visible by this method.
