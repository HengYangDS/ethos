---
subject: ethos:research-change-surfaces-branch-names
role: research
state: active
relations:
  part_of: README.md
  constrained_by: ../../governance/product-design-contract.md
---

# Branch Names in Primary Sources

Research date 2026-11-18. Review by 2027-05-18, or when a forge or a foundation publishes a
naming rule for the branches of coding agents.

Question: is there a consensus standard for branch names, what do the conventions in use make
a name carry, and what do coding agents add?

Every source below is the project's or the vendor's own page or file, read on 2026-11-18. The
findings report what the sources say. The three sections after them are this study's reading.

## What each source prescribes

| Source                                      | Long-lived names                                  | Short-lived names                                                                                   | What the source calls itself                              |
| ------------------------------------------- | ------------------------------------------------- | --------------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| Git, reference names                        | none                                              | syntax alone: no `..`, no control characters, no component that ends in `.lock`                     | the tool's rule                                           |
| Git, its own project's workflow             | `maint`, `master`, `next`, `seen`                 | "topic branches", forked from the oldest branch they will merge into                                | a recommended workflow                                    |
| Git Flow, 2010                              | `master`, `develop`                               | `release-*`, `hotfix-*`; a feature is "anything except" those                                       | "a successful branching model"; its author's note of 2020 |
| GitHub flow                                 | the default branch                                | "a short, descriptive branch name": `increase-test-timeout`                                         | a workflow                                                |
| Trunk-based development                     | trunk                                             | release branches, cut late, never merged back, deleted when the release leaves service              | a practice site                                           |
| Microsoft, Azure Repos guidance, 2026-02-17 | main; `release/20`                                | `users/name/description`, `feature/name`, `bugfix/description`, `hotfix/description`                | "some suggestions"                                        |
| GitLab                                      | default branch; examples `release/*`, `feature/*` | `%{id}-%{title}` from an issue; a leading `123-` links the branch to issue 123                      | product behaviour                                         |
| Conventional Branch 1.1.0                   | `main`, `master`, `develop` without a prefix      | `<type>/<description>`: `feature/` or `feat/`, `bugfix/` or `fix/`, `hotfix/`, `release/`, `chore/` | "a specification", one maintainer, CC BY 4.0              |
| Conventional Commits 1.0.0                  | -                                                 | says nothing about branch names                                                                     | a specification for commit messages                       |
| Gerrit                                      | the target branch                                 | a push to `refs/for/<branch>` means "pushing for review"; the server keeps `refs/changes/NN/NNNN/P` | product behaviour                                         |

Sources: `git help check-ref-format` and `git help workflows` (Git 2.56.1, local manual);
<https://nvie.com/posts/a-successful-git-branching-model/>;
<https://docs.github.com/en/get-started/using-github/github-flow>;
<https://trunkbaseddevelopment.com/branch-for-release/>;
<https://learn.microsoft.com/en-us/azure/devops/repos/git/git-branching-guidance>;
<https://docs.gitlab.com/user/project/repository/branches/>; <https://conventionalbranch.org/>;
<https://www.conventionalcommits.org/en/v1.0.0/>;
<https://gerrit-review.googlesource.com/Documentation/concept-refs-for-namespace.html>.

Git Flow's author added on 2020-03-05 that teams which deliver continuously should "adopt a
much simpler workflow (like GitHub flow)", that the model may still fit software that is
"explicitly versioned", and that "panaceas don't exist".

## What coding agents add

| Source                     | The agent's branch                                                              | What goes with it                                                                       |
| -------------------------- | ------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| GitHub Copilot cloud agent | "a new `copilot/` branch is created ... the agent can only push to that branch" | a draft pull request that a human reviews and merges; the requester cannot approve      |
| Claude Code action         | input `branch_prefix`, default `claude/`                                        | optional commit signing as `claude[bot]`                                                |
| Conventional Branch 1.1.0  | "AI Agent Source Prefixes": `ai/`, `claude/`, `codex/`, `copilot/`, `cursor/`   | a second axis beside the purpose prefixes                                               |
| GitHub rulesets            | rules target branches "whose name matches the pattern you specify"              | restrict creation, update and deletion; "an extra approval" for Copilot's pull requests |

Sources:
<https://docs.github.com/en/copilot/concepts/security-governance-and-network-settings/risks-and-mitigations>;
<https://github.com/anthropics/claude-code-action/blob/main/docs/usage.md>;
<https://conventionalbranch.org/>;
<https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets>.

## What nineteen repositories do

Of the nineteen repositories of the [peer study](peers.md), three prescribe a form for a topic
branch: GitHub Spec Kit (`<type>/<issue-number>-<short-slug>` with `feat/`, `fix/`, `docs/`,
`community/`, `chore/`), gsd-core (`feat/NNN-slug`, `fix/NNN-slug` and the other commit types
as prefixes; `release/X.Y.0` and `hotfix/X.Y.Z` are made by its release workflow alone) and
BMAD-METHOD (`fix/description`). The other sixteen prescribe none. Two keep an integration line
beside a release line: BMAD-METHOD ("branch from `dev` and target `dev`"; "`main` is
release-only") and gsd-core ("two long-lived branches": `main` for production and `next`, its
default, with a validator that corrects a request aimed at the wrong one).

## What a name is asked to carry

The sources load five different things onto one string:

| What                   | Examples                                                  | Who else already holds it                    |
| ---------------------- | --------------------------------------------------------- | -------------------------------------------- |
| The kind of change     | `feat/`, `fix/`, `chore/`, `docs/`                        | the commit type; a label of the request      |
| The place in delivery  | `main`, `develop`, `next`, `release/1.2`, `hotfix/`       | nothing else; this is the branch's own fact  |
| The actor              | `users/name/`, `copilot/`, `claude/`, `dependabot/`       | the commit's author and signer               |
| The tracker's identity | `123-title`, `feat/2342-slug`                             | the request's link to its issue              |
| A step of a protocol   | `refs/for/main`, `seen`, `next`, a merge queue's branches | the forge's review object, where it owns one |

## Patterns that at least three sources share

- No source claims the standing of a standard. Each is guidance, a suggestion, a product's
  behaviour or one maintainer's specification.
- The names of long-lived branches are roles, and the roles are few: a line that is released,
  a line that integrates, and lines kept for a release.
- A short-lived name is a lowercase prefix, a slash and a hyphenated slug, and the prefixes
  come from one small family (`feat`, `fix`, `hotfix`, `release`, `chore`, `docs`).
- A tracker's number in the name is how a branch is tied to its reason.
- A prefix is what a forge's rules match, so a prefix is also a boundary of permission: the
  agent's prefix is the one place the agent may write.
- A head that is offered for review, and is not yet part of any line, gets a name of its own
  wherever a server keeps review: Gerrit's `refs/for`, the Git project's `seen`.

## Where the sources disagree

- **A prefix or none.** GitHub flow and sixteen of nineteen repositories prescribe none;
  Microsoft, Conventional Branch and Spec Kit prescribe one.
- **Where the kind of change lives.** In the branch name for Conventional Branch and Spec Kit;
  in the commit for Conventional Commits, which is silent on branches.
- **Release branches or tags.** Microsoft argues for branches; trunk-based development cuts
  them late or not at all; Git Flow's author limits his own model to versioned software.
- **Whose name an agent's branch carries.** The vendor's (`copilot/`, `claude/`) by default in
  two tools; one generic `ai/` beside them in Conventional Branch.

## Not reached

- OpenAI's page on the branch names of Codex redirected to another host and was not followed;
  Cursor's was not read. Their prefixes are known here only from Conventional Branch's table.
- No source gives a number for the adoption of Conventional Branch.
- GitHub's page on the `refs/pull` namespace was not read.
