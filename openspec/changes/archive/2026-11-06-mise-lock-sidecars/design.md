# Design

## Context

See [proposal.md](proposal.md). `repository_mise_files` returns the config, the lock and any
declared version carriers. `run_mise` writes those materials into a disposable copy, under
`MISE_SAFE=1` and `MISE_LOCKED=1`, and refuses a carrier that differs from the repository's copy.

## Goals / Non-Goals

Goals:

- An npm tool installed through an aube sidecar resolves in the copy exactly as in the repository.

Non-goals:

- Reading any ambient configuration or the repository tree beyond the declared closure.

## Decisions

- **The lock's sidecars belong to the closure.** Every regular file under the lock's sibling
  `locks/` directory is a material, keyed by its repository-relative path, read as text and
  validated by the existing path rules. A sidecar is lock data, so it goes where the lock goes.
- **Only the sidecars the lock names.** The closure reads each `aube.path` that the lock declares,
  relative to the lock's directory. A path outside the repository refuses with
  `mise_lock_sidecar_outside_root`. A named sidecar the tree lacks is left for native mise to
  report.
- **No new refusal for content.** A changed sidecar refuses through the existing
  `mise_version_carrier_changed:<path>`.
- **Native trust policy, unchanged ETHOS trust.** From 2026.11.2, safe mode keeps the aube graph,
  so native mise also resolves a locked aube install for an untrusted configuration. ETHOS still
  carries native trust to its copy only when the root is trusted. It records no trust, keeps no
  state, and runs no repository code. The boundary test now expects native resolution for an
  untrusted copy from 2026.11.2 on, and still checks those three properties.
- **A public version reader.** `mise_version()` replaces the private helper, so tests read the
  selected release without private access.

## Risks / Trade-offs

- A large `locks/` tree adds read time per call; measured repositories hold a few files each.
