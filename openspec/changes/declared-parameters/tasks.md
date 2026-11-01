# Tasks

## 1. Declaration and resolution

- [ ] 1.1 Declare parameters as `[[parameter]]` rows and move the size ceilings into group `size`.
      Done when the size tests pass against the rows.
- [ ] 1.2 Generalize `size_resolution` to every group. Done when a lower value applies, a higher one
      applies only within the bound with a reason, and a restated default, an unknown or retired key
      and a malformed value are gaps for a `timeout` key as for a `size` key.
- [ ] 1.3 Add the invocation accessor and set it in both composition roots. Done when a repository
      value reaches an adapter without the adapter taking the root, and an unbound invocation reads
      the defaults.

## 2. Timeouts

- [ ] 2.1 Give every gate a deadline from its own `timeout_seconds` or `timeout.gate_seconds`, hold
      a declared value to the bound, and declare `local-install-smoke`'s. Done when an undeclared
      gate stops at the repository's value, a gate above the bound is a profile gap, and the full
      proof passes.
- [ ] 2.2 Remove the timeouts of commands inside gates; the formatter's commands, which
      `lane format` and the archive projection also run, take `timeout.tool_seconds`. Done when
      `adapters/gates/` holds no numeric timeout literal and a hung inner command fails as
      `gate_timeout`.
- [ ] 2.3 Route tool, Git, probe, lock, download, request and admission waits through their
      parameters, and make the protocol constants native arguments or named grace and polling
      constants. Done when `src/` holds no literal wait.

## 3. Evidence and check

- [ ] 3.1 Record each gate's effective timeout and its source, and list the invocation's deviations
      in the proof summary. Done when a repository value appears in both with its reason.
- [ ] 3.2 Add the architecture check for literal waits. Done when it reports 0 for `src/`, records
      the count for `tools/`, fails on a planted literal and passes a named grace or polling
      interval.

## 4. Specifications

- [ ] 4.1 Write the `repository-paradigm` and `quality` deltas. Done when strict validation passes.

## Workflow follow-up

- Before landing, the lane's proposal passes on GitHub and GitLab.
- Before the release that carries this Change, each governed repository's latest proof durations are
  read, and a gate above 300 seconds without a declared timeout receives one in that repository's
  binding before it upgrades; GitLab issue #2 receives the release.
