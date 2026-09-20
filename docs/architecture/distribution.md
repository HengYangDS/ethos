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

`distributions/npm` is the current transitional npm launcher. It discovers
a checkout from either the working directory or its own distribution path,
then runs the Python command plane through `uv`. Outside a checkout it falls back to an installed Python
`ethos` module through `python -P -m ethos.cli`. The Node package does not
implement governance logic, mutate repository truth, or define separate public
commands.

The terminal boundary separates installed product identity, exact repository
selection and the repository's own build toolchain. Homebrew is a required
delivery channel; a native formula does not imply a frozen binary. CLI, MCP, SDK
and version-matched Skills share application meaning. An adopter needs neither
ETHOS source nor its development environment. Implementation and acceptance are
tracked in the existing installed-product Change; these are not claims that
Homebrew, portable Skills or installed MCP have shipped.

The present distribution boundary is:

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

- A maintainer host runtime is owned by host software
  supply chain, not by this repository.
- `.config/checks/node/runtime.toml` owns the exact releases used to prove the
  npm launcher and the pinned Linux archive SHA-256 values. The declared set
  contains the selected current LTS and stable release lines.
- The Python distribution declares one platform Node payload solely to execute
  its bundled OpenSpec package without a global Node or PATH fallback. That
  payload owns no repository Node matrix, package workflow, or policy.
- `tools/ci/scripts/install-node.sh` verifies the selected official archive
  against that policy before extraction.
- Hosted npm compatibility jobs select one exact declared release and execute
  `tools/ci/scripts/run-node-compatibility.sh`.
- Hosted packaging uses the policy default; the matrix separately proves every
  declared compatibility release without preserving a future-promotion state.
- IDE-, desktop-, and application-managed Node runtimes remain owned by those
  applications and are not repository mutation targets.

The exact Node proof uses the npm bundled with each official Node archive. The
declared matrix therefore proves Node and its bundled npm as one official
runtime identity rather than declaring a second independently provisioned npm.

Published package scope is intentionally narrower than repository history.
Distribution manifests must use explicit allowlists for neutral launcher assets
and package documentation. They must not publish historical evidence, archived
change records, ignored local state, tests, adopter-private records, host
paths, or person attribution metadata as product defaults. Contributor identity
for enterprises is declared through repository role policy and review evidence,
not through a single built-in package author.
The same active-surface boundary applies to product plans and rule comments:
they may cite generic reference-adopter fixtures and mechanism classes, but not
named private repositories or personal work history as product authority.

Status: see front matter.

Purpose: explain the repository truth represented by this ETHOS document.

See also: [Documentation Root](../README.md), [Command Plane](../reference/command-plane.md), and [Glossary](../reference/glossary.md).
