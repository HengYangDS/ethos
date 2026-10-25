# Proposal

## Why

0.2.0-alpha.13 ships two defects that stop adopters.

ETHOS resolves a repository's locked tools in a disposable copy of its declarations, and mise never trusts that copy. mise selects the installed copy of an aube-locked package only for a trusted configuration, so resolution reports such a tool missing. Architecture Publisher's lane and aigw-cli's Go static analysis stop on it, and web-ingestion-benchmark carries the same kind of lock.

On Windows, the JavaScript behavior gate passes Node's test reporter as an absolute path. Node loads reporters as module URLs and reads `C:\` as the scheme `c:`. Every Windows run therefore ends with an empty journal, and DDWG's hosted verification on `windows-latest` fails this way.

Adopters install only published releases, so they need a successor that carries both fixes. The same release moves ETHOS's own supply to the latest stable releases, so each adopter can refresh its supply and rebind to the release in one pass.

## What Changes

- Before resolving, ETHOS asks native mise whether the repository's configuration root is trusted, using the caller's own trust inputs. Only when mise reports it trusted does resolution carry that trust to its disposable copy of the exact declared bytes, for that invocation, with safe mode and disposable state kept. An untrusted configuration keeps today's result, and the refusal names `mise trust` as the next action. Execution never carries trust.
- The JavaScript behavior gate builds the Node test-runner options in one place and passes the reporter module as a file URL; the journal destination stays a file path.
- codespell and Vale receive `--` before the Markdown inputs, so a file named like an option is read as a file.
- The supply moves to the latest stable releases within ETHOS's constraints:
  - mise 2026.10.19 as the floor and the CI bootstrap;
  - Node 26.12.1, Python 3.14.9, Go 1.27.3, syft 1.55.0 and Vale 3.25.1;
  - OpenSpec 1.15.0, markdownlint-cli2 0.24.0, Allure 3.22.1 and the katex override 0.19.1;
  - the latest stable releases in the Python lock;
  - setup-uv v10.3.2 with uv 0.13.5, docker/login-action v4.7.0 and jdx/mise-action v5.2.3, pinned by commit.

  Python stays at 3.12 to 3.14.
- The release entry: the product version moves to 0.2.0-alpha.14, and the `0.2.0-alpha.14` changelog entry is curated from the Unreleased notes and these fixes.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `quality`: native supply resolution carries the repository's own native trust to its disposable copy, and locked execution never carries resolution trust.

## Impact

Code: `src/ethos/adapters/toolchain/mise.py`, `src/ethos/adapters/gates/javascript/{execution,behavior}.py` and `src/ethos/adapters/gates/tool.py`, with their tests. The supply refresh changes `.config/mise/`, `.config/checks/ci-projection/policy.toml`, `package.json`, `pyproject.toml`, the npm and uv locks, the CI model under `.config/ci/` and its generated provider projections, and the tests that name moved versions. The GitLab supply image moves later, when the GitLab plane is rebuilt. The release entry changes `VERSION`, `CHANGELOG.md`, `distributions/npm/package.json`, `package-lock.json` and the version tests. Adopters receive the fixes from the published 0.2.0-alpha.14 release; the tag, hosted release and adopter rebinds follow the landing as separate effects. Out of scope: mise itself and its trust model, adopters' repositories, and the protected-branch readiness and refresh-provenance defects tracked for later Changes.
