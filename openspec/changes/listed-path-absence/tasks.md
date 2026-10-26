# Tasks

## 1. Listed Path Absence

- [x] 1.1 Prove the race with a regression: a listed path deleted after its existence check leaves reclamation complete, and a dangling listed link still defers it. Done when the deleted case fails against `d03b23798` (it deferred with `[Errno 2]`: `build/evidence/listed-path-absence/red.log`).
- [x] 1.2 Treat a listed path deleted since its check as absent in the observation walk, and keep every other resolution error unknown. Done when both cases and the retirement tests pass and `python_product` does not grow (59 passed, `green.log`; `python_product` stays 69,999; the native `ps` reproduction deferred 62 of 78 calls before and 0 of 72 after, `repro-before.log`, `repro-after.log`).
- [x] 1.3 Make the historical-observation test report the whole result when it fails. Done when the retirement tests pass (`green.log`).
- [x] 1.4 Record the fix under `[Unreleased]` in `CHANGELOG.md`. Done when `markdown_lint` and `prose` pass.
- [x] 1.5 Move the process-listing tests and the shared generation tree out of `test_retirement.py`, so that each module stays within the paradigm's 512 effective lines. Done when the paradigm audit reports no `python-size` gap (`test_retirement.py` 441, `test_retirement_listing.py` 83, `support.py` 13).

## Workflow follow-up

- Prove the exact head and archive this Change. Land only after the release owner has tagged 0.2.0-alpha.16.
