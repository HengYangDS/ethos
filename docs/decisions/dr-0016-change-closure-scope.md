---
subject: ethos:decision:change-closure-scope
role: decision
state: canonical
decision_id: DR-0016
decision_status: accepted
relations:
  current_owner: ../../openspec/config.yaml
---

# DR-0016: Changes Close on Their Delivered Scope

Status: canonical rationale. The OpenSpec configuration owns current behavior.

Date: 2026-10-24.

Purpose: preserve why the 13 Changes open for 0.2.0 were archived with only the tasks they
delivered, how each withdrawn task stays visible in its Change, and when it returns.

See also: [OpenSpec configuration](../../openspec/config.yaml),
[DR-0015: Release stages follow a declared journey scope](dr-0015-release-stage-scope.md), and
the [Terminal Governance Product Design](../plans/terminal-governance-product-design.md).

## Context

On 2026-10-24, 13 Changes held 100 open tasks. DR-0015 had already made a journey that the release
target does not declare, or whose environment is unavailable, "not qualified" instead of a release
blocker, but it kept every open task's done condition. No Change could therefore archive: 51 tasks
waited on an environment that this repository cannot provide, such as the intranet GitLab, an
adopter's own runtime or hosted jobs, the deferred di-effect family, an upstream Mise release, a
soak period, signing credentials or a user decision, and 41 needed in-repo work that 0.2.0 does not
depend on. The open Changes had become a standing queue, and worktrees, lanes and records kept
accumulating beside it. The same day the user directed that worktrees, lanes and Changes converge,
that every Change close, and that tasks waiting on unavailable environments leave 0.2.0 through a
decision record that states why and when they return.

## Decision

A Change closes on its delivered scope. Before its archive, each open task is judged on current
evidence and takes one of four outcomes:

- **Delivered:** current evidence meets its done condition, and the task is checked with that
  evidence.
- **Environment:** it waits on an environment that this repository cannot provide now. It leaves
  the Change and returns when that environment can be observed.
- **In-repo:** its remaining work lies in this repository, but 0.2.0 does not need it. It leaves
  the Change and returns as a new Change when the work is taken up.
- **Superseded:** later work or a decision replaced it. It leaves the Change with that evidence and
  does not return.

A withdrawn task keeps its line, identity and hierarchy in `tasks.md` without a checkbox, marked
`Withdrawn by DR-0016 (environment).`, `(in-repo)` or `(superseded)`, so the archived Change still
shows its whole plan while official progress counts only the tasks it kept. A Change whose open
tasks were all withdrawn records this closing decision as its one checked task. A spec delta merges
only requirements that the product implements; a requirement whose implementation was withdrawn
leaves the delta and returns with its new Change. Each Change then archives through the native
Work Lane archive with its own proof.

## Alternatives Rejected

- **Keep the Changes open until their environments return:** rejected because neither the intranet
  GitLab nor the adopters' environments have a date, so the Changes would stay open indefinitely,
  which is the condition the user asked to end.
- **Check withdrawn tasks or rewrite their done conditions:** rejected because a checkbox would claim
  an acceptance that no evidence shows.
- **Move the withdrawn tasks into one successor Change:** rejected because it keeps an open Change
  without an owner or a date and recreates the queue.
- **Delete the withdrawn lines:** rejected because the archive would then read as if the whole plan
  had been delivered.

## Consequences and Boundary

- Withdrawal claims nothing about the work. It is not completion, and only a superseded task is
  called obsolete.
- Requirements that an earlier archive accepted ahead of their implementation, such as those of
  `proof-throughput` on 2026-10-17, remain in the accepted specifications. The withdrawn task names
  the implementation they still lack, and the Change that restores it cites that task.
- Two deferred actions keep their owner and date outside any Change: `installed-product` 3.2.4
  seals Mise installations once a Mise release carries jdx/mise#14883 (owner a225c731, review
  2026-10-30), and `installed-product` 3.3.2 previews the host-store retirement again after
  2026-10-31 and applies it only on the user's approval.
- Design that only withdrawn tasks would have delivered leaves with them, and the archived designs
  keep its rationale: the Homebrew Cask channel, release signing and notarization, the notarized
  macOS disk image, the Homebrew Python and frozen-bundle builder alternatives, real-client MCP
  qualification before wider mutation exposure, and recovery of formation staging that a crash
  leaves behind.
- A Change that restores a task withdrawn for the intranet GitLab gives the GitLab acceptance its
  own subtask that waits only for the intranet: publish the same objects with `--peer gitlab` and
  read back its hosted CI. The GitHub work completes on its own, as the scenario for one
  unavailable declared peer in the repository-governance specification allows.
- Release entries keep naming unqualified journeys, as DR-0015 requires.
- This record adds no checker, registry or ledger. Official OpenSpec progress, its archive and Git
  keep owning task state and history.

## Evidence and Revisit

On 2026-10-24 the 100 open tasks were judged as 6 delivered, 51 environment, 41 in-repo and 2
superseded. The supply refreshes of 11.3.5, 11.3.6 and the uv 0.13.4 lock superseded
`native-supply-and-configuration` 11.3.2. `dfc17351c`, the rework of the conserved candidate that
`b18465bb0` withdrew, superseded `publication-history-repair` 13.4.6.

| Change                            | Delivered  | Environment                                                                             | In-repo                                                                              | Superseded |
| --------------------------------- | ---------- | --------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ | ---------- |
| `documentation-comprehension`     |            | 12.3, 12.3.2, 12.3.3, 12.4, 12.5, 12.6                                                  | 12.1, 12.4.1                                                                         |            |
| `feedback-and-skill-closure`      |            | 13.2, 13.2.3, 13.3                                                                      | 13.2.1, 13.2.2                                                                       |            |
| `greenfield-formation`            | 2.4        | 2.3                                                                                     |                                                                                      |            |
| `hosted-verification`             |            | 7.11, 7.11.2, 7.12, 7.13                                                                | 7.3                                                                                  |            |
| `installed-product`               | 3.2.5, 3.8 | 1.8, 3.2, 3.2.4, 3.3, 3.3.2, 3.5, 3.6, 3.7, 3.10, 3.11, 4.3, 4.5, 4.5.9, 4.5.10, 4.5.11 | 1.3, 1.5, 2.3, 2.4, 3.4, 4.1, 4.2, 4.5.12                                            |            |
| `legacy-carrier-retirement`       |            | 2.16, 2.19                                                                              |                                                                                      |            |
| `merge-continuation-acceptance`   |            |                                                                                         | 4.16, 13.4.4, 13.4.4.1                                                               |            |
| `native-supply-and-configuration` | 11.8       | 11.3, 11.3.7, 11.4, 11.4.2                                                              | 11.3.1                                                                               | 11.3.2     |
| `owned-resource-recovery`         |            | 5.11, 5.12, 5.12.1, 5.13                                                                | 5.6                                                                                  |            |
| `proof-critical-path`             |            |                                                                                         | 1.11, 2.12, 2.13, 2.14, 9.1, 9.2, 9.3, 9.5                                           |            |
| `publication-history-repair`      | 13.4.5     | 13.4, 13.4.2, 13.4.2.2, 13.4.3, 13.4.9                                                  | 13.4.10                                                                              | 13.4.6     |
| `quality-evidence-admission`      | 10.13      | 11.9, 11.9.1, 11.9.2, 11.9.2.1, 11.9.2.8, 11.9.2.9, 11.9.2.10                           | 8.9, 8.10, 8.11, 8.12, 8.13, 10.4, 10.6, 10.6.1, 10.7, 10.11, 10.12, 10.14, 11.9.2.7 |            |
| `structural-simplification`       |            |                                                                                         | 9.9                                                                                  |            |

Revisit when an environment named by a withdrawn task becomes available, such as the intranet
GitLab or an adopter's installed runtime, or when a new Change restores a withdrawn task.
