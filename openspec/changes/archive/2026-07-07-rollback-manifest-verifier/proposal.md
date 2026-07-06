# Rollback Manifest Verifier

## Why

The rollback-window retirement gate must not be closable by editing
`.ethos/profile.toml` alone. A profile can declare completed scenarios, but the
final embedded-backend retirement path needs trust-bearing evidence that is
tracked, repository-local, head-bound, and scenario-complete.

## What Changed

- Strengthen `ethos fleet retirement-readiness` so terminal rollback-window
  readiness validates the evidence manifest itself.
- Require the manifest to be Git-tracked, TOML-readable, bound to reachable
  adopter and external ETHOS heads, and backed by per-scenario evidence,
  command, digest, target-head, and product-head fields.
- Keep adopter binding generic through `.ethos/profile.toml` and `.config/`;
  do not introduce product-core adopter directories.
