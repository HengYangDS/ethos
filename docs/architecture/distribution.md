---
subject: ethos:distribution
role: reference
state: canonical
relations:
  canonical_for: npm and package distribution adapters
---

# Distribution

ETHOS distribution adapters make the command plane reachable from ecosystem
package managers without owning command semantics.

`packages/ethos-node` is the npm launcher. It first looks for an ETHOS source
checkout and runs the Python command plane through `uv`; outside a checkout it
falls back to an installed Python `ethos` module. The Node package does not
implement governance logic, mutate repository truth, or define separate public
commands.

The distribution boundary is:

- Python packages own kernel, governance, workspace, project, agent, and CLI
  behavior.
- Node package metadata owns npm `bin` exposure and launcher UX only.
- Source checkout execution uses `uv run --package ethos ethos`.
- Installed execution uses `python -m ethos.cli` until a published Python wheel
  is available for `uvx` or `pipx` based installs.

This keeps npm, PyPI, GitLab, and future package managers as adapters over one
ETHOS command plane.
