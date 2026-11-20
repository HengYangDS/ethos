---
subject: ethos:research-change-surfaces-templates
role: research
state: active
relations:
  part_of: README.md
  constrained_by: ../../governance/product-design-contract.md
---

# Issue and Change Templates in Primary Sources

Research date 2026-11-18. Review by 2027-05-18, or when GitHub ships forms for pull requests or
a forge ships a field for an agent's authorship.

Question: what do a forge's issue forms and the description of a pull or merge request hold in
mature projects, what do the forges themselves provide, and what do coding agents change?

Every source below is the forge's, the project's or the paper's own page or file, read on
2026-11-18, except one secondary article that is named as such. The findings report what the
sources say. The three sections after them are this study's reading.

## What the forges provide

| Forge  | Issues                                                                                                                                                                                         | Changes                                                                                                                                                               |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GitHub | YAML forms under `.github/ISSUE_TEMPLATE/` with typed fields and `required`; `labels`, `type`, `projects`, `assignees`; a chooser `config.yml` with `blank_issues_enabled` and `contact_links` | one Markdown file, or several under `PULL_REQUEST_TEMPLATE/`; no form                                                                                                 |
| GitLab | Markdown under `.gitlab/issue_templates/`; `Default.md`; quick actions such as `/label ~bug` in the template                                                                                   | Markdown under `.gitlab/merge_request_templates/`; in the default one, variables such as `%{all_commits}`, `%{closes_issue}`, `%{co_authored_by}`, `%{source_branch}` |

Sources:
<https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/about-issue-and-pull-request-templates>;
<https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms>;
<https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/configuring-issue-templates-for-your-repository>;
<https://docs.gitlab.com/user/project/description_templates/>.

GitHub's page on issue forms says that they are "in public preview". A form's answers become
"a standard markdown issue comment".

## What guidance says

- **A change description.** Google's guide: a first line that is a "short summary of what is
  being done", a "complete sentence, written as though it was an order", and a body that says
  what and why; descriptions written by tools "should also follow the advice"; the author checks
  that "the description still reflects what the CL does" before submitting
  (<https://google.github.io/eng-practices/review/developer/cl-descriptions.html>).
- **An issue for an agent.** GitHub's guide to its coding agent: "A clear description of the
  problem", "Complete acceptance criteria on what a good solution looks like", "Directions about
  which files need to be changed"; "think of the issue you assign to Copilot as a prompt"
  (<https://docs.github.com/en/copilot/tutorials/cloud-agent/get-the-best-results>).
- **Instructions for agents.** AGENTS.md is "a dedicated, predictable place" for them, the
  nearest file wins, and it is "stewarded by the Agentic AI Foundation under the Linux
  Foundation"; GitHub's agent reads `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` and its own files
  (<https://agents.md/>, the guide above).

## What nineteen repositories hold

The files are those of each repository's default branch on 2026-11-18, kept with the
[peer study](peers.md).

| Practice                                               | Repositories, of 19 |
| ------------------------------------------------------ | ------------------- |
| YAML issue forms                                       | 13                  |
| Contact links for questions or security in the chooser | 11                  |
| Blank issues closed                                    | 10                  |
| A form each for a bug, a feature and documentation     | 4                   |
| A change template                                      | 13                  |
| A change template of two to five sections              | 10                  |
| An agent or AI use named in the change template        | 7                   |
| One change template for each kind of change            | 1 (gsd-core)        |
| A non-empty `AGENTS.md`, or a `CLAUDE.md`, at the root | 14                  |
| An `AI_POLICY.md` at the root                          | 1 (Ghostty)         |

The counts are a script's over the collected files (`counts.py` beside the collection); a form
is counted by its file name, so a repository that names its forms otherwise is undercounted.

Fields of an issue form that recur where agents are in play: the agent and the model (OpenSpec,
Spec Kit, BMAD-METHOD, Claude Code, Codex); a session trace (OpenSpec); acceptance criteria
(required for a feature in OpenHands and gsd-core, optional in Spec Kit); "Done when" for a
chore (gsd-core); an AI disclosure (Spec Kit, required); a checklist before submission (Claude
Code, gsd-core).

Sections of a change template, in the words of the files:

| Repository  | Sections                                                                                                                               |
| ----------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| uv          | Summary; Test Plan                                                                                                                     |
| OpenSpec    | `Closes #`; What this changes; How you verified it; two checkboxes                                                                     |
| Zed         | Summary; Testing; Self-review                                                                                                          |
| BMAD-METHOD | What; Why; How; Testing                                                                                                                |
| Spec Kit    | Description; Testing; AI Disclosure                                                                                                    |
| Kubernetes  | What type of PR is this; What this PR does and why; Which issues; Special notes for your reviewer; a release note; AI usage disclosure |
| GitHub CLI  | Description; How did you test this change; Key points; Notes for reviewers; Authorship and follow-up                                   |
| OpenHands   | a `HUMAN:` part and an `AGENT:` part; Why; Summary; Issue Number; How to Test; Type                                                    |
| Gemini CLI  | Summary; Details; Related Issues; How to Validate; Pre-Merge Checklist                                                                 |

## What agents changed in these files

| Mechanism                                 | Where                | The file's own words                                                                                                                                     |
| ----------------------------------------- | -------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A disclosure in the change                | Kubernetes           | "Mention "YES" or "NO". If yes, briefly describe how AI was used."                                                                                       |
| A disclosure with tool, model and mode    | Spec Kit             | "names the agent/tool, model(s), settings/mode (reasoning effort; autonomous vs. human-supervised), and extent"                                          |
| A disclosure at every later step          | Spec Kit             | "A PR-body disclosure does not cover later commits or review rounds."                                                                                    |
| A trailer on each agent's commit          | Spec Kit             | "`Assisted-by: GitHub Copilot (model: Claude Opus 4.8, autonomous)`"                                                                                     |
| No trailer for the agent                  | Kubernetes           | "Do not add `Co-authored-by:` in commit messages"                                                                                                        |
| Who wrote it, who answers                 | GitHub CLI           | "An agent wrote it independently, and no human has guided the implementation beyond the initial prompt."; "Nobody has explicitly committed to replying." |
| Only what was done counts as a test       | GitHub CLI           | "Report only actions you actually performed and results you actually observed"; "write `Not tested` and explain why"                                     |
| No account of how the change was produced | GitHub CLI           | "Do not narrate how the pull request was produced or refer to private conversations, prior agent work"                                                   |
| A part that only the human writes         | OpenHands            | "The `HUMAN:` section ... is reserved for human contributors only. AI agents must not add to, edit, move, or remove it."                                 |
| Evidence that the change runs             | OpenHands            | "Just running unit tests is NOT sufficient. Explain exactly what command you ran"                                                                        |
| The agent named and the result verified   | OpenSpec             | "If a coding agent wrote this, named the agent and model above, and verified the result myself"                                                          |
| A policy file                             | Ghostty; Zed; Astral | "All AI usage in any form must be disclosed."; "The human-in-the-loop must fully understand all code."                                                   |

Sources: the repositories' files under `.github/`, `AGENTS.md`, `CONTRIBUTING.md` and
`AI_POLICY.md` at <https://github.com/kubernetes/kubernetes>, <https://github.com/github/spec-kit>,
<https://github.com/cli/cli>, <https://github.com/OpenHands/OpenHands>,
<https://github.com/Fission-AI/OpenSpec>, <https://github.com/ghostty-org/ghostty>,
<https://github.com/zed-industries/zed>, <https://github.com/astral-sh/uv>,
<https://github.com/bmad-code-org/BMAD-METHOD>, <https://github.com/google-gemini/gemini-cli>.

## What the Linux kernel did with its tag

The kernel's page for coding assistants, in the documentation of version 7.0, has a section
"Attribution": "Contributions should include an Assisted-by tag in the following format:
Assisted-by: AGENT_NAME:MODEL_VERSION [TOOL1] [TOOL2]". The same page in the current
documentation (7.4.0-rc3) has no such section and no such tag. Both versions keep: "AI agents
MUST NOT add Signed-off-by tags. Only humans can legally certify the Developer Certificate of
Origin", and the human submitter is responsible for "Reviewing all AI-generated code" and
"Taking full responsibility for the contribution"
(<https://www.kernel.org/doc/html/v7.0/process/coding-assistants.html>,
<https://docs.kernel.org/process/coding-assistants.html>).

A secondary article of 2026-10-22 reports that the maintainers agreed to deprecate the tag and
gives as reasons that it could not be enforced and that a required tag "wasn't delivering
reliable signal"; it links no primary source, and this study did not find the list's own posts
(<https://www.mindstudio.ai/blog/linux-kernel-ai-disclosure-tag-removed>).

## What measurements say

- A study of 33,596 pull requests written by five coding agents (the AIDev data set): the merge
  rates differ by agent from 43.0% to 82.6%; "More structured PR descriptions are associated
  with faster reviewer responses and shorter completion times"; "structured descriptions do not
  guarantee merges, and code quality remains a central factor"; the authors "describe
  descriptive patterns ... rather than causal effects" (<https://arxiv.org/abs/2602.17084>,
  submitted 2026-02-19).
- A second study of the same data, by its abstract: "reviewer engagement has the strongest
  correlation with successful integration"; larger changes and "coordination-disrupting actions,
  such as force pushes, are associated with a lower likelihood of merging"
  (<https://arxiv.org/abs/2602.19441>, submitted 2026-02-23; the full text could not be read).

## Patterns that at least three sources share

- Intake is a typed form, one for each kind of report, and free-form issues are closed off or
  sent elsewhere.
- A change description answers three questions: what changed and why, how it was verified, and
  which issue it serves. Everything else is a project's own.
- Where agents report or build, the form asks which agent and model, and the change says who
  is answerable.
- A feature states its acceptance criteria before work starts.
- Instructions for agents live in one file at the root, and the change template points to it.

## Where the sources disagree

- **Whether a declared disclosure is worth asking for.** Spec Kit asks for it at every step and
  on every commit; Kubernetes asks once in the change and forbids the trailer; the kernel asked
  for a trailer and withdrew it.
- **Whether a checklist proves anything.** Gemini CLI's template has eighteen checkboxes and
  gsd-core's up to twenty-eight; uv's has none; the GitHub CLI's says that automated results
  "do not belong here" because a reviewer sees them in CI.
- **Who may open a change.** Anyone in most; maintainers and invited contributors in OpenSpec;
  anyone with an approved issue in gsd-core; at most three open at once for one account in
  Spec Kit.
- **Whether outside rules bind maintainers.** Ghostty's policy exempts them; the others do not
  say.

## Not reached

- The full text of the second study, and any study that ties one field of a template to an
  outcome; the first study compares agents, not fields.
- The kernel list's own record of the decision on its tag.
- GitHub's page on several pull request templates and the `template` query parameter.
- GitLab's own project templates, which its documentation names as its example.
