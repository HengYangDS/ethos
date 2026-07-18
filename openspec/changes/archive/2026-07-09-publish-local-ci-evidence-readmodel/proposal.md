# Publish Local CI Evidence Readmodel

## Summary

Expose local CI fallback evidence freshness in `ethos publish --json` so local
readiness cannot be mistaken for hosted CI or remote publication.

## Scope

- Add a HEAD-bound fallback evidence manifest at
  `build/evidence/local-ci/fallback.json` when local CI runs.
- Report missing, invalid, stale, and current fallback evidence in publish JSON.
- Keep remote push and hosted CI claims separate from local fallback evidence.

## Non-goals

- Do not push to the remote.
- Do not claim hosted CI success from local evidence.
- Do not create a new publication center; this is a read-model hardening of the
  existing publish/local-ci boundary.
