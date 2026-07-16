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

- Python packages own core, contracts, repository, assistants, adapters, test,
  and CLI behavior.
- Node package metadata owns npm `bin` exposure and launcher UX only.
- Source checkout execution uses `uv run --package ethos ethos`.
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
  Node 24.18.0 and Node 26.5.0.
- `tools/ci/scripts/install-node.sh` verifies the selected official archive
  against that policy before extraction.
- Hosted npm compatibility jobs select one exact declared release and execute
  `tools/ci/scripts/run-node-compatibility.sh`.
- Hosted packaging keeps the installer default at Node 24.18.0 so compatibility
  expansion does not silently promote the release baseline.
- IDE-, desktop-, and application-managed Node runtimes remain owned by those
  applications and are not repository mutation targets.

Node 26.5.0 is the next default candidate, not the current default. The date
2026-10-28 is only the earliest review trigger. Promotion requires current
release-status verification, successful hosted compatibility results, package
proof, and a separate reviewed repository change; the date alone performs no
transition.

The exact Node proof uses the npm bundled with each official Node archive. The
local Linux runs for Node 24.18.0 and 26.5.0 both supplied npm 11.11.0. The
repository keeps `packageManager = "npm@11.12.1"`, but this change does not
provision or prove that npm release. Package-manager supply and enforcement are
a separate reviewed decision so the Node matrix does not silently change two
runtime variables at once.

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
