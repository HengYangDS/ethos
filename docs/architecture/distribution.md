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
- Explicit source execution uses `uv run python -m ethos.cli`; the installed
  console selects a repository-bound runtime when present.
- Installed execution uses `ethos`. `python -m ethos.cli` deliberately executes
  the caller-selected package for development and recovery, not host dispatch.
- Native distribution archives reuse the verified portable runtime and exact
  wheel. Their Homebrew Cask is a generated transport projection; archive,
  installation and remote publication acceptance remain distinct.

This keeps npm, PyPI, GitLab, and future package managers as adapters over one
ETHOS command plane.

## Node Runtime Compatibility

`.config/mise/config.toml` selects the exact Node release; its native lock owns
platform archive URLs and SHA-256 digests. CI versions are compiled projections
of that declaration, not another compatibility or checksum policy.

- `tools/ci/toolchain/native.py --mise` prepares and verifies the official archive
  through the existing Mise download, cache, lock and scratch owners. Source
  execution consumes only that verified cache, never ambient Node or npm.
- The Python wheel carries the qualified Node-only runtime under `resources/node`.
  The existing `package.json` and `package-lock.json` uniquely select the product
  npm module, shipped with the other locked product modules. Installed execution
  uses that module with the shipped Node executable, without adopter source,
  global installation or PATH fallback. Package builds consume prepared supply
  and never download it.
- Hosted bootstrap synchronizes build-only Python dependencies and then the
  editable project, prepares native supply and installs locked npm packages with
  `NodeRuntime.executable` and `.npm`. The Linux supply image copies the complete
  source import closure only during construction and removes it before shipping;
  checkout-owned verification rechecks cached bytes before execution.
- Native Nox `javascript_tests` executes package behavior on the selected supply.
  Host conformance retains Linux, macOS and Windows qualification; compilation
  alone does not prove a hosted job, built image or installed successor.
- Official GNU/Linux archives require glibc 2.28 or newer; they are not musl
  support or manylinux certification. Platform wheel tags and runtime acceptance
  remain obligations of the native supply and packaging owners.
- Host-, IDE-, desktop- and application-managed runtimes retain their own
  installation owners and are not repository mutation targets.

The native Node archive retains bundled npm only as a verified build-only seed
for the first script-disabled locked install. It is excluded from the emitted
wheel and is not the product npm authority. Subsequent commands resolve the
package-lock-owned npm module through the existing runtime resolver; CI has no
separate npm version selector or installer. Local audit disposition never
permits CI, public release or distribution.

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
