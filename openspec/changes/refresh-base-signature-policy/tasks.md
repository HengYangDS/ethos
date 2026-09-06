## 1. Contract And RED

- [x] 1.1 Strictly validate the modified command-plane and
  repository-governance requirements.
- [x] 1.2 Add minimal failing tests for optional and malformed tracked policy,
  rejected identity fields, subject validation, tracked signing overriding
  ambient configuration, complete replay-range verification, exact zero-residue
  failure, and removal of the no-consumer CI bootstrap.

## 2. Unique Owner And Migration

- [x] 2.1 Introduce one repository commit-policy compiler and migrate product
  audit, Git execution, and lifecycle subject validation to consume it.
- [x] 2.2 Make refresh use native rebase with the policy-derived environment and
  validate every replayed subject and required signature before Git-common
  effects.
- [x] 2.3 Expose an explicit validated archive subject when a repository's grammar
  rejects the semantic default.
- [x] 2.4 Delete the old policy loader, hard-coded message module, unused report
  schema, dead Git-worktree commit surface, CI checkout bootstrap, duplicated
  parsers, stale tests, identity fields, and all compatibility residue.
- [x] 2.5 Reuse the product schema validator for the complete schema tree and
  delete the redundant `check-jsonschema` dependency.

## 3. Closure

- [x] 3.1 Prove repository-wide reference closure and net semantic reduction.
- [x] 3.2 Run focused tests, Ruff format/check, typing, module-layout,
  import-boundary, schema, CI projection, and strict OpenSpec validation.
