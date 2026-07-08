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
