---
subject: ethos:distribution
role: explanation
state: canonical
relations:
  canonical_for: npm and package distribution adapters
---

# Distribution

ETHOS distribution adapters make the command plane reachable from ecosystem
package managers without owning command semantics.

`distributions/npm` is the npm launcher. It runs the Python command plane
through `uv` only when the launcher is executing from this source checkout's
own distribution path. Outside a checkout it falls back to an installed Python
`ethos` module through `python -P -m ethos.cli`. The Node package does not
implement governance logic, mutate repository truth, or define separate public
commands.

The distribution boundary is:

- The Python `ethos` package owns the kernel, contracts, repository, assistants,
  adapters, and CLI behavior. Tests are not shipped.
- Node package metadata owns npm `bin` exposure and launcher UX only.
- Source checkout execution uses `uv run ethos`.
- Installed execution uses `python -P -m ethos.cli` until a published Python
  wheel is available for `uvx` or `pipx` based installs.

This keeps npm, PyPI, GitLab, and future package managers as adapters over one
ETHOS command plane.

## Node Runtime Compatibility

Node runtime ownership remains layered rather than mechanically unified:

- A maintainer workstation runtime is owned by the workstation software
  supply chain, not by this repository.
- `.config/checks/node/runtime.toml` owns the exact releases used to prove the
  npm launcher and the pinned Linux archive SHA-256 values. The current set is
  the latest LTS Node 24.19.0 and latest stable Node 26.7.0.
- The Python distribution declares one platform Node payload solely to execute
  its bundled OpenSpec package without a global Node or PATH fallback. That
  payload owns no repository Node matrix, package workflow, or policy.
- `tools/ci/scripts/install-node.sh` verifies the selected official archive
  against that policy before extraction.
- Hosted npm compatibility jobs select one exact declared release and execute
  `tools/ci/scripts/run-node-compatibility.sh`.
- Hosted packaging uses Node 26.7.0; the matrix separately proves the latest
  Node 24 LTS without preserving a future-promotion state.
- IDE-, desktop-, and application-managed Node runtimes remain owned by those
  applications and are not repository mutation targets.

The exact Node proof uses the npm bundled with each official Node archive. The
declared matrix therefore proves Node and its bundled npm as one official
runtime identity rather than declaring a second independently provisioned npm.

Published package scope is intentionally narrower than repository history.
Distribution manifests must use explicit allowlists for neutral launcher assets
and package documentation. They must not publish historical evidence, archived
change records, ignored local state, tests, adopter-private records, workstation
paths, or person attribution metadata as product defaults. Contributor identity
for enterprises is declared through repository role policy and review evidence,
not through a single built-in package author.
The same active-surface boundary applies to product plans and rule comments:
they may cite generic reference-adopter fixtures and mechanism classes, but not
named private repositories or personal work history as product authority.

Status: see front matter.

Purpose: explain the repository truth represented by this ETHOS document.

See also: [Documentation Index](../index.md), [Command Plane](../reference/command-plane.md), and [Glossary](../reference/glossary.md).
