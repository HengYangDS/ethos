---
subject: docs:start
role: how-to
state: active
relations:
  canonical_for: first run
---

# Quickstart

Status: active.

Purpose: give a first-run path for inspecting a repository, planning proof,
and understanding the mutation boundary.

See also: [Command Plane](../reference/command-plane.md) and
[Glossary](../reference/glossary.md).

## First Hour

Start with the single bounded reader:

```bash
ethos status
```

`ethos status` is the single bounded reader for humans and agents. It answers
where you are, what you may do, which foreign Work Lanes and unbound Work Lane
refs are visible, whether readiness is gapped, and which command should run
next without minting repository truth.

Use `--json` when an agent or script needs stable evidence. Adoption has one
read-only plan and one binding carrier:

```bash
ethos adopt --root <repo> --json
```

Review `read_files`, `planned_files`, `write_plan`, `required_gaps`, and
`rollback`. The apply criteria are:

- `planned_files` contains only `.ethos/profile.toml`;
- `required_gaps` is empty, especially no `adoption_conflict:<path>` entries;
- rollback is clear: remove `rollback.generated_files` or restore the
  pre-adoption Git state.

Apply only with explicit authorization and the current HEAD:

```bash
ethos adopt --root <repo> --apply --authorize --expect-head <git-head> --json
```

If the repository is not tracked by Git yet, initialize Git first or use the
dry-run plan as a review artifact without claiming HEAD-bound adoption.

After the binding is applied, use the five-command lifecycle loop:

```bash
ethos status
ethos plan --changed
ethos prove
ethos land
ethos publish
```

For scripts and agents, `ethos status --json` exposes the safe first-glance
fields in `summary`: current role, dirty state, changed-path count, visible
foreign Work Lane count, visible unbound Work Lane ref count, missing-lease
count, dirty foreign Work Lane count, advisory coordination count, and whether
coordination is currently blocking. Treat those fields as visibility only;
inspect `data.coordination` before any handoff, merge, land, retirement, or
cleanup decision.

Common next actions:

- `git_repository_missing`: initialize Git or run from a repository root.
- edit blocked on a protected checkout: switch to an editable checkout before
  changing tracked files.
- land target not ready: keep the result at local proof/readiness and ask the
  maintainer to prepare the landing target.
- `expected_head_mismatch`: refresh the plan against the current HEAD.
- hosted CI unavailable: keep the claim local-ready only.
- domain gates: declare them in the adopter profile, let `ethos plan` select
  the mapped proof gates, and use `ethos status` to keep local evidence separate
  from hosted or domain-specific proof. Product core must not hardcode domain
  names.

## Maintainer Reference

Advanced commands remain available for maintainers and evidence work, but they
are not part of the first-hour path:

First validation path:

```bash
ethos status --json
ethos plan --changed --json
ethos prove --execute
ethos --help
```

For governance and discovery:

```bash
ethos doctor
ethos adopt --root <repo> --json
ethos fleet inspect --target .
ethos playbooks check
ethos prove --gate docs-registry --gate docs-topology
ethos prove --gate schemas
ethos prove --json
ethos assistants doctor
ethos campaign hypotheses
```

Mutation defaults to dry-run/readiness. Apply paths require explicit
authorization and an expected HEAD.
