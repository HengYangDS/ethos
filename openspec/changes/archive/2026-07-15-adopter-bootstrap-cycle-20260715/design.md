## Context

Scope coverage receives names selected by the lifecycle report. The report
excludes `no-tasks`; however, the official OpenSpec creator initially emits
that status. The existing scope bootstrap already enforces an absent
material-path declaration, a tracked profile, exactly one requested path, and
one real Change directory.

## Goals / Non-Goals

**Goals:** Admit the first profile declaration for the sole fresh official
Change and preserve the current fail-closed boundaries.

**Non-Goals:** Do not make `no-tasks` a normal active Change, a general scope
provider, or a way to write a scope companion together with the profile.

## Decisions

Pass a separately derived singleton `no-tasks` candidate only to the
profile-bootstrap branch. Normal scope declarations continue to receive the
existing active/archiving selection. The scope function retains all existing
profile/path/tracking checks, so lifecycle status alone grants no authority.

## Risks / Trade-offs

[Over-broad selection] → restrict fallback to one official list item with
status `no-tasks`; test ordinary material-path coverage remains blocked.

[Future CLI status drift] → no unknown status is admitted; the prior selected
sets remain unchanged outside the explicit fallback.
