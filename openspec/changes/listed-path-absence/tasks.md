# Tasks

## 1. Listed Path Absence

- [ ] 1.1 Prove the race with a regression: a listed path deleted after its existence check leaves reclamation complete, and a dangling listed link still defers it. Done when the deleted case fails against `d03b23798`.
- [ ] 1.2 Treat a listed path deleted since its check as absent in the observation walk, and keep every other resolution error unknown. Done when both cases and the retirement tests pass and `python_product` does not grow.
- [ ] 1.3 Make the historical-observation test report the whole result when it fails. Done when the retirement tests pass.
- [ ] 1.4 Record the fix under `[Unreleased]` in `CHANGELOG.md`. Done when `markdown_lint` and `prose` pass.

## Workflow follow-up

- Prove the exact head and archive this Change. Land only after the release owner has tagged 0.2.0-alpha.16.
