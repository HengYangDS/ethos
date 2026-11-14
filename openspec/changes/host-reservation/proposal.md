# Proposal

## Why

`host-reservation` opens Family 4 of the release-candidate plan, after the archive of `rc-plan`,
and implements decision 11 of the common-base design together with gate item R12. At the base
commit the host queue has one entrant and no reader: a foreground host proof runs its gates with no
admission at all (`src/ethos/application/proof/host.py:42-109`), a ticket records its repository's
absolute path and the contention gap prints it (`src/ethos/adapters/gates/host_admission.py:168-172`),
`ethos host` has one command, and nothing checks the guests' virtual CPUs against the reservation
that `reserved_cpus` declares.

## What Changes

- A foreground host proof runs its readiness gates without waiting, then holds the host ticket for
  its test and package gates, with the ticket's token and worker cap exported to them.
- A ticket records the operation and the owner mark its holder declared, keeping its three older
  fields for the engines of earlier releases that share the directory.
- One projection prints no repository path: the contention gap names the operation, the pid and the
  start time, and the owner mark is visible only to the holder's own repository.
- The worker cap only lowers a worker count that the caller's environment already declares.
- `ethos host status` is the one read: the declaration, the load and every live ticket in arrival
  order, and `--guest-cpus N` checks the guests' count against `reserved_cpus`.
- A guide covers a host that runs CI guests.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: MODIFIED `Heavy local work is admitted host-wide`, `The host declaration bounds
admitted work` and `Full proofs and nested work share the host admission`; ADDED `One read lists
the host queue and its holder` and `The guests' CPUs are checked against the reservation`.
- `command-plane`: MODIFIED `Group commands are catalog operations`.

## Impact

`src/ethos/adapters/gates/host_admission.py` and `proof_slot.py`, `src/ethos/application/host.py`,
`application/proof/host.py` and the catalog, `src/ethos/contracts/operations/host.py`,
`system/surfaces.toml`, the guide `docs/guides/ci-guest-host.md` with its index line,
`docs/reference/command-plane.md`, their tests and `CHANGELOG.md`. The contention gap changes its
form, which the Unreleased entry names as breaking. The host declaration file and its keys do not
change.
