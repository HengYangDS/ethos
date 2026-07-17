## MODIFIED Requirements

### Requirement: Python Vulnerability Audit Gate

ETHOS SHALL run Python dependency vulnerability auditing through a reusable owner
script that uses a supported resolved dependency input, keeps scanner claim
boundaries explicit, and retries only classified transient transport failures
before parsing scanner output. The retry policy SHALL use a fixed bounded attempt
limit and SHALL fail closed when the scanner reports vulnerabilities, emits
malformed JSON, or fails for any unclassified reason.

#### Scenario: pip-audit scans uv-exported resolved requirements

- **WHEN** hosted CI, local CI, or `ethos prove --execute --json` runs the Python
  vulnerability audit gate
- **THEN** ETHOS SHALL invoke `tools/ci/scripts/run-python-vulnerability-audit.sh`
- **AND** the runner SHALL export a frozen resolved requirements input from
  `uv.lock` before invoking `pip-audit`
- **AND** the runner SHALL invoke `pip-audit` with `--no-deps --disable-pip` so
  the exported pinned input is audited without dependency resolution or a pip
  bootstrap step
- **AND** the evidence SHALL be local owner-gate evidence under
  `build/evidence/quality/security/`
- **AND** the gate SHALL NOT claim that `pip-audit` reads `uv.lock` directly
- **AND** the gate SHALL NOT claim OSV scanner coverage, image/package scanning,
  hosted CI success, or remote publication.

#### Scenario: transient scanner transport disconnect is retried within bounds

- **WHEN** `pip-audit` fails before producing usable JSON with a classified
  transient transport-disconnect diagnostic
- **THEN** the owner script SHALL retry at most once after a fixed delay
- **AND** it SHALL continue only if a later attempt succeeds with valid JSON
- **AND** it SHALL not create tracked retry state or transform the resulting
  evidence into hosted-provider proof.

#### Scenario: vulnerability or non-transient scanner failure remains final

- **WHEN** `pip-audit` reports a vulnerability, produces malformed JSON, or
  fails with an unclassified diagnostic
- **THEN** the owner script SHALL return a nonzero result without retrying that
  result
- **AND** it SHALL NOT emit a passing vulnerability-audit summary.
