# Design

## Context

See [proposal.md](proposal.md).

- `materialize_tool` accepts an explicit `mise`, and without one it looks on PATH
  (`mise_executable`).
- `tools/ci/toolchain/native.py`'s `prepare_mise` returns the operator's mise when one is on PATH.
  Otherwise it stages the version pinned in `.config/mise/config.toml` in the tool cache and verifies
  its digest. `tools/ci/delivery/distribution.py` and the journey already pass it explicitly.
- On every GitHub host-conformance leg, `nox -s host_conformance` builds the wheel and runs the
  install smoke. The smoke keeps the runtime archive and writes
  `build/evidence/local-install/smoke.json`, which `nox -s supply_chain` reads when it gets no
  `--host`. The local `release-sbom` gate catalogs the archive the same way.

## Goals / Non-Goals

Goals:

- A tools/ci session gets each native tool the same way on every host, whatever a job stages.
- Every step that catalogs a release platform's archive runs on that platform before any tag.
- One registry names the native tools that can be staged.

Non-goals:

- Running the binary scan on every commit. The scan never blocks a release, it now gets Grype like
  any session, and a `scan_tag` dispatch regenerates any report. Running it per commit would
  download Grype's database on every run for a report that blocks nothing.
- Rehearsing the release-mode build, the publication, the scan and the journey before a tag. They
  still run only at release time, and a separate Change owns their rehearsal.

## Decisions

- **Supply tools through the repository's mise, not through staging lists.**
  - An earlier draft declared each session's tools, scanned session code for them, and checked
    every job's staging list against them. Two reviews rejected it. The scan could not follow
    string imports, attribute calls or computed names. It also kept the staging lists as a second
    statement of each session's needs.
  - Passing the repository's mise at the call site removes the dependence on PATH that made the
    staging lists matter.
  - The architecture test keeps it that way: in tools/ci, only `native.py` may call
    `materialize_tool`.
- **Match legs from the declaration.** CUE renders each release leg's `os` and `python` as a pair.
  The host-conformance step runs only when its own pair is among them, so a change to a release leg
  moves the coverage with it, including the emulated Windows on Arm interpreter.
- **The log is the evidence.** `supply_chain` prints its evidence, including components that it
  declared from the locked supply. Host conformance keeps its one receipt upload.
- **One tool registry.** `native.py`'s choices become `NATIVE_BACKENDS` plus `node`.

## Risks / Trade-offs

- A job that runs a session without prefetching its tool downloads that tool during the session.
  The download is the same one prefetching would make, only later.
- On the operator's host, `prepare_mise` still prefers the mise on PATH when it meets the pinned
  minimum. The installs remain locked to `mise.lock`, so the supplied tool is the same.
