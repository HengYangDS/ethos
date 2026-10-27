# Tasks

## 1. Supply Refresh

- [x] 1.1 Publish supply for the accepted checkout. Done when the hosted offline smoke passes and the published digest is read back (run `40531973403`, source `ad9108d70`, digest `425cd202cd0fbb1243e80a64eb18bc4feabc9a0a3a293c75d6546e1bf2941498`).
- [x] 1.2 Bind the published digest through the CUE owner and regenerate projections. Done when `lane project --check` passes and every GitLab supply job selects that digest (`lane project --check`: pass).
- [x] 1.3 Validate the authored intent and CI carriers. Done when native OpenSpec task parsing, formatting, repository hygiene, configuration quality and shell lint pass (OpenSpec and native Prettier: pass; Nox hygiene, shell, config and CI sessions: pass).

## Workflow follow-up

- Run exact committed full proof, archive this source-only Change, integrate and publish its object to accepted and release branches, and verify hosted acceptance on both peers.
- Retire this owned Work Lane after verified acceptance and preservation of its evidence.
