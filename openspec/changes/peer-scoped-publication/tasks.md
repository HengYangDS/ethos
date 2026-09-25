# Tasks

## 1. Reproduce the missing publication path

- [x] 1.1 Add a public two-peer fixture where one declared peer is unreachable; verify the existing all-peer request remains unknown and cannot publish the healthy peer.
- [x] 1.2 Add selected-peer positive and negative cases for accepted, proposal and release roles, invalid selectors, receipt rebinding and exact continuation scope; verify the old command fails for the intended reason.

## 2. Repair at the existing owners

- [x] 2.1 Add explicit peer selection to the `publish` CLI and application request boundary without changing the default all-peer request or the typed effect schema.
- [x] 2.2 Recheck selected ID-to-remote bindings before and between effects; keep proof, source, ref policy and exact-CAS checks fail-closed on receipt replay.
- [x] 2.3 Report declared, selected and unselected peers accurately; preserve selected peers in retry guidance and update the command reference without claiming global publication.

## 3. Verify source

- [x] 3.1 Run strict official OpenSpec, affected publication and release suites, repository format/lint and diff hygiene; keep accepted-ref effects and installed adopter replay outside this checklist.
