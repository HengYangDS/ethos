# Design

## Context

See [proposal.md](proposal.md). The CUE owner already records the same constraint for Allure:
"GitHub retains raw Allure results; GitLab's instance artifact limit cannot hold them."

## Goals / Non-Goals

Goals:

- GitLab verify jobs upload within the instance limit.
- The rule is stated once, so a later path cannot bring a build output back.

Non-goals:

- Changing GitHub's artifacts, which the release job consumes.
- Raising the instance limit, which is an infrastructure decision for the owner.

## Decisions

- **Evidence only on GitLab.** The archive keeps proof, test, coverage, security, secrets and
  release evidence. The comment beside it names the Python distributions with the Allure results as
  GitHub-retained.
- **A projection test.** It reads `.gitlab-ci.yml`, collects every job's `artifacts.paths`, and
  requires none to lie under `build/artifacts/`.

## Risks / Trade-offs

- The GitLab archive still grows with the SBOMs, which grow with the runtime. The test bounds what
  kind of file it holds, not its size; a size check would need the instance limit, which the
  repository does not declare.
