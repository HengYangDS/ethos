# Design

## Context

`distributions/npm` holds a launcher package (`package.json` with `bin.ethos`, `bin/ethos.mjs`,
`README.md`). Its consumers are all inside the repository:

- the root `package.json` scripts `ethos` and `test:npm`, and `tests/architecture/npm-package.test.mjs`,
  which the `javascript_tests` session runs with `distributions/**/*.mjs` in its coverage;
- the release identity, which requires the launcher's version to equal `VERSION`
  (`repository/release/identity.py`, `projected_package_versions`) and refuses a version in the
  root `package.json` or `package-lock.json`;
- the product boundary, which audits the launcher's `files` allowlist and `bin`
  (`repository/policy/boundary/product.py`, `catalog.py`), and format selection, which owns
  `distributions/npm/`;
- the distribution specification's launcher requirements and the README, release guide and
  distribution explanation.

The pipeline has no npm publication step, and the manifest's URLs are placeholders.

## Goals / Non-Goals

Goals:

- No npm launcher, no second version carrier, no launcher requirement.
- Keep the guards that still protect the repository: no version in the root Node manifests, and a
  root package with workspaces stays private.

Non-Goals:

- Node itself: the JavaScript tools (Prettier, OpenSpec, Markdown and link checks) keep the locked
  Node runtime and npm supply.
- Other channels, which DR-0022 and the release Changes own.

## Decisions

1. **Delete, do not deprecate.** Nothing outside the repository consumes the launcher, so a
   deprecation window would only keep a second carrier alive.
2. **One version carrier.** `projected_package_versions` becomes a check that the root
   `package.json` and `package-lock.json` carry no product version, named for that purpose; the
   release configuration calls it whenever either file exists.
3. **The boundary keeps its root rule.** The root workspace-privacy finding stays; the launcher's
   allowlist, `bin` and file-scope findings and their constants go.
4. **The specification states what remains.** The launcher requirements are removed with their
   reason, and the Node runtime requirement names the JavaScript tools and drops
   `npm run ethos` and `npm run test:npm`.

## Risks / Trade-offs

- Someone running `npm run ethos` from a checkout loses that entry; `uv run ethos` and the installed
  `ethos` remain, and the changelog names the removal.
