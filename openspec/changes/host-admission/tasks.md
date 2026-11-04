# Tasks

## 1. Host admission

- [x] 1.1 Read the host declaration. Done when tests show that `slots` and `reserved_cpus` default
      to 1 and 0, that a value out of range or an unreadable file reports a named gap, and that the
      worker cap is the CPUs left, at least 1. The module was absent when its tests first ran; the
      9 declaration cases now pass.
- [x] 1.2 Queue owned tickets in arrival order. Done when tests show that two runs serialize in
      order, that `slots = 2` admits two, that a dead holder's place frees without cleanup, and that
      a wait that reaches its bound reports the holder's repository, executable and start time. A
      live lock counts before its record exists, and a departing run removes its lock file; the
      first run left three lock files behind.
- [x] 1.3 Add `ethos host run`. Done when tests show that the child runs admitted with the worker
      cap, that its exit status returns unchanged, that nested work joins its ticket only while the
      holder lives, and that the ticket records no arguments. The 3 CLI tests and the join and
      copied-token case pass.
- [x] 1.4 Take the host slot in a full proof, after the repository slot and before the load wait.
      Done when proof tests show that order, and that a host without a load average records the
      load as not measured. Both new tests failed first, on the missing token and the missing
      `load_measured`; the 27 proof slot tests now pass.
- [ ] 1.5 Record the change in the Unreleased notes and the CLI reference. Done when the changelog
      and documentation gates pass.

## 2. Specification

- [x] 2.1 Write the `quality` delta. Done when strict validation and the cumulative archive
      simulation pass. Both pass, with all 12 specifications valid.

## Workflow follow-up

- After the release ships, tell AIGW the Change and release, so it writes this workstation's
  `host.toml` and starts the 7-day acceptance from runner job timings.
