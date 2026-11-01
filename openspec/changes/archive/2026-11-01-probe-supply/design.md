# Design

## Context

See [proposal.md](proposal.md). The Python behavior probe selects its toolchain through the
repository's own Mise declaration when one exists: `repository_mise_files` finds the configuration,
and `locked_tool` resolves `uv` and `python` from it offline, refusing an undeclared or uninstalled
tool. ETHOS's `[tools]` table lists `python` but not `uv`. The hosted supply prepares Mise tools in
`mise_tool_paths`: online it runs `mise install --locked cue github:rhysd/actionlint` plus Node and
Go when declared, and offline, inside the GitLab image, `require_cached_mise_tools` checks that
cue, actionlint and Node resolve. The GitLab image runs the same preparation when it is built.

## Goals / Non-Goals

**Goals:**

- ETHOS declares the tools its shipped probe needs, as governed repositories do.
- Both hosted planes provide every declared Mise tool among Node, Python and uv.
- Every pin names the latest stable release that ETHOS's constraints admit.

**Non-Goals:**

- Running ETHOS's suite through the probe, which `test-runner-unification` does.
- Python 3.15, which `requires-python` excludes.
- Rebinding the GitLab supply image, which is built from the landed head and bound in its own
  Change.

## Decisions

- **Declared tools, not flags.** The native supply derives the Mise tools it installs from the
  `[tools]` table, as it already does for Node and Go, instead of a new command-line option per
  job. A repository that declares uv in Mise gets it on every hosted job that prepares Mise.
  Rejected: installing Python and uv only in the jobs that run the probe, which would need a
  job-specific list that the CUE model and every job must keep in step.
- **uv 0.13.6 in Mise.** It is the latest release and the version `uv.lock`, setup-uv and the
  supply image already select, so the pin adds no new version; `mise lock` writes its entries for
  the six platforms the lock already covers.
- **Native resolvers select every version.** `uv lock --upgrade` and `mise lock` write the locks; no
  lock entry is edited by hand. Floors follow the Python lock.
- **GitLab receives the head with its binding.** `dev` goes to GitHub first, the hosted
  `supply_image` workflow builds the image from it, and both peers receive `dev` once the binding
  lands, so GitLab never runs a head whose inputs differ from its bound image.

## Risks / Trade-offs

- [Mise's Python download makes every GitHub job that prepares Mise slower] → Measured on the first
  hosted runs after landing; the cost buys the probe's interpreter on every plane.
- [A moved package changes a finding or a warning that `filterwarnings = ["error"]` turns into a
  failure] → The proof runs every gate on the moved supply; a repair it requires lands here.
- [The operator's uv on PATH differs from Mise's] → Inside the repository, Mise's tasks and the
  probe resolve Mise's uv 0.13.6, the version every other owner already pins.
