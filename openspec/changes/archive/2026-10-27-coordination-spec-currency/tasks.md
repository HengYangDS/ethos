# Tasks

## 1. Accepted Spec

- [x] 1.1 Verify every claim of the 11 planned requirement texts against the code at the lane's base. Done when each claim has a verdict with file and line evidence (audit V1 at `ad9108d70`; knowledge-currency changed no code).
- [x] 1.2 Write the five modified requirements and the six replacements. Done when strict validation passes.
- [x] 1.3 Simulate the archive and validate every spec strictly. Done when no requirement exceeds 500 characters and every spec validates (12 specs valid after the simulated archive: `build/evidence/coordination-spec-currency/archive-simulation.log`).

## 2. Record

- [x] 2.1 Record the Change under `[Unreleased]` in `CHANGELOG.md`. Done when `markdown_lint` and `prose` pass.

## Workflow follow-up

- Prove the exact head, archive this Change, prove the archived head, land it and publish `dev` to GitHub.
