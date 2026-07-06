# OpenSpec Semantic Capability Layout Evidence

Date: 2026-07-06
Work Lane: `work/openspec-semantic-capability-layout`
Closeout mode: local only; remote GitLab is temporarily unavailable.
OpenSpec carrier: `openspec/changes/archive/2026-07-06-openspec-semantic-capability-layout-20260706`.

## Claim Boundary

This evidence binds the archived OpenSpec change
`openspec/changes/archive/2026-07-06-openspec-semantic-capability-layout-20260706` to the repository mutation that
renames accepted OpenSpec capability IDs from stale package-shaped names to
stable semantic capability names while preserving the official flat OpenSpec
shape `openspec/specs/<capability>/spec.md`.

The claim also binds the absorbed quality-gate improvements for this lane:
configuration separation, owner-script CI projection, parallel timeout-bound
tests, generated test evidence under `build/evidence/quality/tests/`, repository
hygiene, and Google-style docstring governance.

## Local Closeout Evidence

- `openspec validate --all --strict --json` passed after archive with 9/9 accepted specs and 0 active changes.
- `ETHOS_ROOT=$PWD uv run --group dev ethos openspec --lifecycle --json` passed after archive with no active lifecycle gap.
- `.config/ci/scripts/run-python-lint.sh` passed.
- `.config/ci/scripts/run-config-lint.sh` passed.
- `.config/ci/scripts/run-shell-lint.sh` passed.
- `.config/ci/scripts/run-docstring-coverage.sh` passed.
- `.config/ci/scripts/run-repository-hygiene.sh` passed.
- `.agents/skills/ethos-quality-gate-governance/scripts/quality_audit.py .`
  passed.
- `.config/ci/scripts/run-python-tests.sh` passed with 767 tests and 95.04%
  coverage; coverage XML was written to
  `build/evidence/quality/tests/coverage/coverage.xml`.
- `ETHOS_ROOT=$PWD uv run --group dev ethos quality coverage --json` passed.
- `ETHOS_ROOT=$PWD uv run --group dev ethos quality types --json` passed.
- `ETHOS_ROOT=$PWD uv run --group dev ethos quality projection-drift --json`
  passed.
- `ETHOS_ROOT=$PWD uv run --group dev ethos quality claims --json` passed.
- `ETHOS_ROOT=$PWD uv run --group dev ethos report --json` passed with
  governance gap count 0 and parity pending count 0.
- `ETHOS_ROOT=$PWD uv run --group dev ethos playbooks check --mode v2-strict --json`
  passed after rebinding the `ethos-quality-gate-governance` package digest.
- `ETHOS_ROOT=$PWD uv run --group dev ethos audit --mode shape --json` passed.
- `ETHOS_ROOT=$PWD uv run --group dev ethos prove --execute --expect-head $(git rev-parse HEAD) --json`
  passed locally before archive; final head-bound proof is rerun by closeout after
  this evidence and claim digest are stable.
- `openspec archive openspec-semantic-capability-layout-20260706 --skip-specs --yes --json`
  moved the completed carrier to archive without refusing official OpenSpec shape.

## Remote Boundary

This evidence does not claim remote GitLab CI, push, merge request, or hosted
publication. Remote publication remains deferred until GitLab is reachable.
Local proof, local candidate landing, and accepted-root closeout are separate
from remote publication.
