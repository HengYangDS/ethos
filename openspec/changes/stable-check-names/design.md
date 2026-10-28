# Design

## Context

See [proposal.md](proposal.md). Read on 2026-10-28 with `gh api`: ruleset 25827049 ("ETHOS protected branches") targets `refs/heads/dev` and `refs/heads/main`. Its rules are deletion, non-fast-forward, linear history, signatures, a pull request with one approval, and 12 required checks pinned to GitHub Actions (app 15368). On `f699fa6cc`, `quality gates`, `repository proof` and `package artifacts` match their check runs; the nine `<os> / Python <v>` contexts match none.

## Goals / Non-Goals

**Goals:**

- Required check names stay valid across supply changes.
- The regression states the identity rule on both forges.

**Non-Goals:**

- Changing the ruleset, or deriving its required contexts from `pipeline.cue`, which `forge-admission-and-assurance` owns.
- Changing which jobs run, or on which runners.

## Decisions

### 1. The name comes from the matrix coordinates

`host-conformance` runs over two axes, `os` and `python`, and Node is locked, not varied. Its name is `${{ matrix.os }} / Python ${{ matrix.python }}`. Every other projected job keeps its name. The GitLab projection has no matrix job, so each of its names is already constant.

### 2. The regression states the identity

The projection test that required the Node version in the job name is replaced. For every projected job, the expressions in its name are exactly its declared matrix axes, and its remaining text is fixed. A supply version can then never enter a required check name.

### 3. The ruleset stays as it is

Changing the ruleset to the versioned names would break again at the next Node bump. The ruleset's own terms, `<os> / Python <v>`, are already the stable identities.

## Risks / Trade-offs

- [The Node version disappears from the job title] → the job's supply steps still print the locked runtime, and mise selects it as before.
- [A later Change adds a matrix axis] → the regression then requires that axis in the name, which keeps checks distinct.
