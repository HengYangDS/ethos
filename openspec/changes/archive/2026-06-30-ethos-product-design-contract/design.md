## Context

`<repo>` is the ETHOS product truth target, but reference-adopter still
contains a richer embedded implementation that acts as migration oracle and
rollback anchor. Deleting or ignoring that implementation would remove safety
controls before external parity exists.

## Decisions

- Define ETHOS from the kernel chain, not from current folders.
- Treat current external packages as migration hosts.
- Treat reference-adopter embedded ETHOS as frozen fallback only after external
  shadow parity and reversible backend switch.
- Keep non-Python distribution adapters outside the Python product ontology.
- Establish the capability parity ledger before code migration.

## Non-Goals

- Do not publish to PyPI, npm, Docker, Homebrew, GitHub Action, or GitLab
  Component.
- Do not delete reference-adopter embedded ETHOS.
- Do not perform package migration in this design change.
