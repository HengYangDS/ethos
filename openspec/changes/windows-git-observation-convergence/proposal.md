## Why

Native Windows package conformance exposes a false dirty-worktree result in the
generated adopter immediately before Work Lane bootstrap. The fixture currently
protects only its byte-round-trip probes, while ordinary tracked text remains
dependent on ambient `core.autocrlf`; ETHOS correctly hides that ambient Git
configuration and therefore observes different semantics from those used to
create the repository.

## What Changes

- Make the generated adopter own canonical text normalization for all ordinary
  tracked text while retaining byte-preserving rules for the explicit LF/CRLF
  probes.
- Add a regression that creates the adopter under a global
  `core.autocrlf=true` policy, simulates CRLF checkout bytes, and requires both
  ambient Git and ETHOS's isolated observation to report a clean repository.
- Keep ambient Git configuration hidden; do not weaken dirty admission, add a
  Windows-only branch, or reinterpret an unavailable observation as clean.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The existing `proof-hosts` requirement already requires repository-local
Git semantics for host-conformance fixtures. This Change corrects its incomplete
implementation and therefore sets `skip_specs: true`.

## Impact

The change is limited to the package-acceptance adopter fixture and its focused
regression. It restores the already-specified Windows host-conformance boundary
without changing production Git observation or adopter repository policy.
