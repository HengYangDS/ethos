# Proposal

## Why

Heavy local work on a shared host starves everything else on it. On 11-04 AIGW asked, with the
user's approval, that ETHOS own one host-wide admission rule, because three CI virtual machines
with 12 of the host's 18 logical CPUs share the workstation with full proofs, renders and test
suites. ETHOS's proof admission holds one slot per repository, so two repositories' proofs overlap,
and nothing else waits: focused proofs, Nox sessions, renders and MLX runs start at once. A full
proof's own workers took the 1-minute load to 72 during alpha.29's proof.

## What Changes

- A host-wide slot beside the repository proof slot. A full proof takes its repository slot, then
  the host slot, then waits for load, so two repositories' proofs no longer overlap. Waiters are
  served in first-come order, a holder that dies releases its place, and every pinned ETHOS engine
  from this release on reads the same versioned protocol.
- `ethos host run [--wait <seconds>] -- <command...>` admits any heavy command the same way and
  runs it as its child. Work that ETHOS already admitted is not admitted twice.
- One host declaration, `host.toml` in ETHOS's host root, carries `slots` (default 1) and
  `reserved_cpus` (default 0). An out-of-range value is refused with a named gap, never clamped.
- Admitted work receives one worker cap: `PYTEST_XDIST_AUTO_NUM_WORKERS` and the neutral
  `ETHOS_HOST_CPU_CAP`, derived from the CPUs that the declaration leaves.
- The load limit stays half the CPUs and keeps counting the virtual machines' measured load; on a
  host without a load average, admission reports the load as not measured.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: heavy local work is admitted host-wide, and a full proof takes the host slot.

## Impact

`src/ethos/adapters/gates/proof_slot.py`, a new host admission module and CLI command, the CLI
reference, the proof tests and the changelog. CI guests cannot take a host lock, so this bounds
local work only; AIGW writes this workstation's `host.toml` when the release ships and retires the
manual START and DONE proof messages once every repository runs the release.
