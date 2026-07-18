## Context

OpenSpec is the mandatory governance carrier for this non-trivial command-plane,
admission, report, publish, and quality-gate hardening. The public product
command plane remains `ethos ...`; OpenSpec records the change contract and does
not become a second runtime.

The active Work Lane is `work/review-hardening`. The change follows the ETHOS
principle of destructive convergence: once the current owner and contract are
identified, old aliases, compatibility helpers, and retired state names are
removed or migrated instead of preserved.

## Design

### Fail-closed proof and transition semantics

`ethos prove` is a transition command and proof gate. A gapped proof must be
machine-refusing, not merely human-readable. The CLI result emitter already
supports enforced non-zero exit on blocking verdicts, so `prove` no longer opts
out of enforcement. Regression tests exercise process status and JSON content.

### Shell admission owner and protected-root deny-by-default

Protected roots are observe-only unless a command is explicitly read-only or a
write path goes through prewrite. Command-risk classification lives in the
admission shell owner module. The prior private-helper surface is not retained in
`admission.core`; tests and callers move to the current owner contract.

### Work Lane lease and actor binding

Tracked writes in a Work Lane require a real ETHOS lease and an actor match. The
prewrite report fails if a raw Git worktree has no lease or if `ETHOS_ACTOR` does
not equal the lane owner. This makes multi-agent visibility non-authorizing:
foreign lanes remain observable but not writable.

### Candidate ref movement proof gate

Candidate movement is part of the same trust path as accepted-root movement.
Direct candidate ref updates require executed proof bound to the new head. The
sanctioned `land` implementation carries an explicit ref-move allowance so the
guard does not self-deadlock while still blocking raw ref mutation.

### HEAD-bound claims and freshness

Claims and evidence freshness are only meaningful for the current repository
truth. Status, plan, report, and quality surfaces pass current Git HEAD into the
claim/freshness read model so stale active claims are visible as current gaps.

### Report read model and score honesty

`ethos report` remains a scorecard, not a transition command. Its summary now
exposes the governed profile, read-model identifier, terminal-control state,
nominal score, effective score, hard-quality gap count, and coordination-risk
count. Hard-floor gaps and coordination risk cannot be hidden behind a green
nominal score.

### Publish local readiness without old state residue

Publish is local readiness plus a deferred remote-publication boundary. The
current state name is `local_publish_ready`. The retired state name is not kept
as an alias in code, tests, schemas, samples, projections, or current docs.
Archived prose that described the prior current state is updated as vocabulary
cleanup under this carrier so repository-visible current wording does not teach
old semantics.

### Local-ci owner projection

Local-ci fallback evidence is a local substitute for hosted CI status only. The
fallback package reads owner scripts from the target repository root's
`.config/ci/scripts/run-local-ci.sh`, not from ambient process cwd, and publishes
those owner scripts in the publish/local-submit package. This prevents `--root`
runs from projecting another checkout's local-ci shape.

### Supply-chain hardening

Release supply-chain evidence is upgraded in four ways:

1. The gitleaks installer uses cached downloads but validates the archive against
   pinned SHA-256 values before extraction.
2. The secrets gate runs both a current working-tree scan and a Git-history scan.
3. SBOM projection includes workspace packages from `pyproject.toml` and
   transitive packages from `uv.lock`, with a lockfile digest and layer counts.
4. Release attestation includes SLSA materials for the repository head, evidence
   digest, `uv.lock`, and SBOM digest.

## Alternatives

Keeping `prove` fail-open and asking every CI/hook caller to parse JSON was
rejected. Keeping old publish state names or private admission helper exports was
also rejected because it would preserve compatibility residue after the current
contract is known.

Treating local-ci fallback as a static list was rejected because it drifts from
the owner script. Treating supply-chain evidence as planned-only was rejected for
release-profile readiness: checksum, history scan, transitive dependency, and
attestation materials are current hardening requirements.

## Proof Strategy

- Focused red/green tests for proof exit status, shell admission, prewrite
  lease/actor binding, candidate ref movement, HEAD-bound claims/freshness,
  report read model, publish state/local-ci projection, and supply-chain assets.
- Architecture tests for installer checksum and secret history scan script shape.
- Release tests for lockfile transitive SBOM and SLSA materials.
- `ethos openspec --lifecycle --json` for this active carrier.
- `ethos playbooks route --changed --json` and `ethos plan --changed --json` for
  changed-scope routing.
- Head-bound `ethos prove --execute --expect-head <HEAD> --json` before closeout.
