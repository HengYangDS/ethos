---
subject: docs:start
role: workflow
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

Start with read-only orientation:

```bash
ethos orient
```

`ethos orient` is a first-glance projection for humans and agents. It answers
where you are, what you may do, which foreign Work Lanes and unbound Work Lane
refs are visible, whether readiness is gapped, and which command should run
next. It reads `status` and `report`; it is not a transition verb and does not
mint repository truth.

Use `--json` when an agent or script needs stable evidence, then choose a profile:

| Profile | Use when | Reads | Plans to write |
| --- | --- | --- | --- |
| `generic` | Any Git repository needs the ETHOS loop | `.git`, README, package hints | `.ethos/`, `.agents/`, docs, OpenSpec, claims |
| `python` | A Python package or app is present | `pyproject.toml`, lock files, test/lint config | Python proof gates and workspace profile |
| `monorepo` | Multiple packages share one repository | workspace manifests, `packages/*` | package map and changed-scope routing |
| `github` | GitHub Actions is the hosted projection | `.github/workflows/*`, remote metadata when available | hosted CI projection only |
| `gitlab` | GitLab CI/MR is the hosted projection | `.gitlab-ci.yml`, GitLab templates | hosted CI/MR projection only |

Preview before applying:

```bash
ethos adopt --profile python --dry-run --json
```

Use the dry-run output to review generated files. The important fields are
`detected_profile`, `requested_profile`, `profile_match`, `observed_files`,
`write_plan`, `required_gaps`, and `rollback`. The apply criteria are:

- the profile matches the repository shape;
- `write_plan` contains only expected ETHOS governance files;
- `required_gaps` is empty, especially no `adoption_conflict:<path>` entries;
- no hosted CI or remote publication is claimed from local evidence;
- rollback is clear: remove `rollback.generated_files` or restore the
  pre-adoption Git state.

Apply only with explicit authorization and the current HEAD:

```bash
ethos adopt --profile python --apply --authorize --expect-head <git-head> --json
```

If the repository is not tracked by Git yet, initialize Git first or use the
dry-run plan as a review artifact without claiming HEAD-bound adoption.

After the scaffold is applied, re-orient and use the five-command transition
loop:

```bash
ethos orient
ethos status
ethos plan --changed
ethos prove
ethos land
ethos publish
```

Use `--json` for stable machine output. report is the payoff view, not a
transition:

```bash
ethos report
```

Common next actions:

- `git_repository_missing`: initialize Git or run from a repository root.
- edit blocked on a protected checkout: switch to an editable checkout before
  changing tracked files.
- land target not ready: keep the result at local proof/readiness and ask the
  maintainer to prepare the landing target.
- `expected_head_mismatch`: refresh the plan against the current HEAD.
- hosted CI unavailable: keep the claim local-ready only.
- domain gates: declare them in the adopter profile, let `ethos plan` select
  the mapped proof gates, and use `ethos report` to keep local evidence separate
  from hosted or domain-specific proof. Product core must not hardcode domain
  names.

## Maintainer Reference

Advanced commands remain available for maintainers and evidence work, but they
are not part of the first-hour path:

First validation path:

```bash
ethos orient --json
ethos status --json
ethos prove --execute
ethos quality command-examples
```

For governance and discovery:

```bash
ethos doctor
ethos init --profile gitlab --dry-run
ethos adopt --profile gitlab --dry-run
ethos fleet inspect --target .
ethos playbooks check
ethos quality docs
ethos quality schemas
ethos quality gates
ethos quality provenance
ethos assistants doctor
ethos campaign hypotheses
```

Mutation defaults to dry-run/readiness. Apply paths require explicit
authorization and an expected HEAD.
