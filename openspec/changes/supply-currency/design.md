# Design

## Context

See [proposal.md](proposal.md). Each pin has one owner: `pyproject.toml` and `uv.lock` for Python,
`package.json` and `package-lock.json` for npm, `.config/mise/config.toml` and `mise.lock` for
native tools, the ci-projection policy for the Mise executables that CI bootstraps,
`.config/ci/*.cue` for the CI model, and the supply Dockerfile for the GitLab image. The provider
workflows are generated from the CUE model. The supply image hashes eight of these inputs, and
GitLab checks that manifest against every checkout.

## Goals / Non-Goals

**Goals:**

- Every pin names the latest stable release that ETHOS's constraints admit, selected by its owner's
  native resolver.
- The shipped advisories are restated from the release build's audit of the moved supply.

**Non-Goals:**

- Python 3.15, which `requires-python` excludes, and any prerelease or yanked release.
- Rebinding the GitLab supply image. It is built from the landed head, so its binding follows in its
  own Change.
- Removing the coupling between a hashed input and the image binding.

## Decisions

- **Native resolvers select every version.** `uv lock --upgrade`, `npm install` and `mise lock`
  write the locks; no lock entry is edited by hand. Floors follow the Python lock because the
  dependency declaration check requires each direct floor to equal its locked version.
- **The GitHub Arm64 runner stays `ubuntu-24.04-arm`.** Ubuntu 26.04 Arm runners are generally
  available, but GitHub still maps `ubuntu-latest`, which the x64 jobs use, to 24.04. Moving one
  architecture alone would split the Linux hosts, so the label moves when `ubuntu-latest` does.
- **ty moves within its Beta line.** No stable ty exists; 0.0.95 is its newest release.
- **re2js takes 2.9.1.** markdownlint 0.42.0, still the latest, pins 2.8.6, which
  GHSA-gg6h-894w-4m9c affects; the override already lifts it past that pin, and 2.9.1 is the latest
  release.
- **minimatch and glob cross the majors that their consumers declare.** The fixes exist only in
  minimatch 11 and glob 14, while the latest ESLint, `@eslint/config-array` and `test-exclude`
  declare minimatch 10 and glob 13. Those consumers call only `minimatch()`, `Minimatch#match`,
  `glob()` and `globSync()`, which both majors keep; glob 13 relies on minimatch internals that 11
  removes, so the two move together. npm's own bundled copies cannot be overridden and stay
  reported, as its bundled undici and ip-address are.
- **OpenSpec 1.16.0 is checked against the governed repositories first.** Its strict validation
  reported no finding that 1.15.0 does not report, in ETHOS or in the ten governed repositories with
  OpenSpec content.
- **GitLab receives the head with its binding.** `dev` goes to GitHub first, the hosted
  `supply_image` workflow builds the image from it, and both peers receive `dev` once the binding
  lands, so GitLab never runs a head whose inputs differ from its bound image.

## Risks / Trade-offs

- [A moved tool changes findings: Ruff rules and formatting, ty diagnostics, or a pytest deprecation
  that `filterwarnings = ["error"]` turns into a failure] → The proof runs every gate on the moved
  supply. A repair that the move requires lands in this Change.
- [CPython 3.14.10 or another moved artifact carries an advisory] → The 3.14.9 approval does not
  cover 3.14.10, and no other finding is waived. The release build's audit runs on the moved head
  before the proof, and a fixable finding blocks it.
- [hatchling 1.33.0 changes the built wheel] → The package and reproducibility gates rebuild and
  check it.
- [minimatch 11 or glob 14 matches differently for a consumer, for example a trailing empty segment
  or an ignore pattern that starts with `/`] → ESLint, the JavaScript coverage gate and the test
  report run on the overridden packages in the proof.
- [The operator's Mise is older than the new floor] → Mise refuses a configuration whose floor it
  does not meet; Homebrew ships 2026.10.24.
