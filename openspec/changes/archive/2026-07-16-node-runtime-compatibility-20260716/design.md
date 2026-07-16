# Node Runtime Compatibility Design

## Context

The distribution capability owns the npm launcher boundary. The repository
needs exact hosted evidence without claiming that workstation, IDE, desktop,
and hosted-provider runtimes share one installation owner.

## Design

`.config/checks/node/runtime.toml` declares the current hosted default, the exact
compatibility set, the next default candidate, and the earliest review date.
`tools/ci/scripts/run-node-compatibility.sh` parses that policy with Python
`tomllib`, resolves the requested matrix release, rejects an active-runtime
mismatch before npm executes, and runs the existing launcher acceptance
sequence with engine-strict enabled through the process environment.

The GitLab template is the provider projection owner. Its npm verification job
selects Node 24.18.0 and Node 26.5.0 through one exact matrix, installs the
selected release, and calls the reusable runner. `.gitlab-ci.yml` remains a
byte-identical projection. The npm packaging job does not set `NODE_VERSION`,
so `tools/ci/scripts/install-node.sh` keeps Node 24.18.0 as its default.

The date 2026-10-28 does not mutate policy. On or after that date, a separate
change may evaluate current official release status, hosted compatibility
results, package evidence, and rollback readiness before deciding whether to
promote Node 26.

The compatibility runner intentionally uses the npm bundled with each official
Node archive. Both local Linux proof runs supplied npm 11.11.0. The existing
`packageManager = "npm@11.12.1"` declaration remains unchanged and is not
claimed as proven by this change; provisioning or enforcing one npm release
across both Node versions requires a separate package-manager supply decision.

Executable-source growth is recorded as named, measured compression debt under
the repository source-budget policy. The debt expires at the Node 26 review
gate and must be repaid by consolidating the fake-process test scaffolding and
compatibility-runner parsing without removing the exact matrix contract.

## Alternatives

A single system-wide Node rewrite was rejected because workstation,
application-managed, and hosted runtimes have different owners. An unversioned
major-only CI matrix was rejected because it would drift without a reviewed
repository change. Duplicating npm commands inline in provider YAML was rejected
because it would make the provider projection a second policy owner.

## Proof Strategy

Architecture tests parse the TOML policy, check the executable owner script,
assert the exact GitLab matrix and unchanged packaging default, and preserve CI
template parity. Behavioral tests execute the runner with fake Node and npm
binaries to prove command order, engine-strict propagation, and fail-fast
mismatch behavior. Isolated Linux runs execute the owner under both exact Node
releases. Config lint, shell lint, strict OpenSpec validation, quality audit,
and HEAD-bound ETHOS proof close the repository evidence boundary.

## Rollback

Revert the compatibility change. The hosted npm verification job returns to one
Node 24 path, while workstation and application-managed runtimes remain
untouched. Historical proof remains evidence of what was tested, not authority
to rewrite current runtimes.
