## Why

The expert review found that ETHOS had several terminal-hardening gaps where a
human-readable or locally convenient surface could diverge from the governed
contract:

- blocking `ethos prove` verdicts could still exit with status code 0;
- protected-root shell pre-run admission was too optimistic for unknown commands;
- Work Lane writes were not hard-bound to both lease owner and runtime actor;
- candidate ref movement could bypass the same proof discipline expected of the
  accepted root;
- active claims and evidence freshness could be read without binding to current
  HEAD;
- report scorecards could look fully green while hard quality or coordination
  risk remained present;
- publish readiness vocabulary blurred local readiness and remote publication;
- local-ci fallback output could drift from the owner script and from the target
  repository root; and
- release supply-chain evidence lacked checksum-pinned tool download, history
  secret scan, transitive lockfile SBOM, and lockfile/SBOM attestation material.

The user also reaffirmed a product principle: ETHOS does not keep compatibility
residue after destructive convergence. Old state names, helper re-exports,
legacy aliases, and compatibility wrappers must be deleted or migrated to the
current owner contract rather than retained as shadow surfaces.

## What Changes

- Make blocking proof verdicts fail closed at the CLI process boundary.
- Move protected-root shell command classification into its current admission
  owner and deny unknown protected-root mutation unless paths/prewrite bind it.
- Require Work Lane prewrite admission to match active lease owner and
  `ETHOS_ACTOR`.
- Protect candidate ref movement with executed proof bound to the new candidate
  head, while sanctioned land uses the explicit ref-move allowance.
- Bind claims and evidence freshness callers to current Git HEAD.
- Extend report summary/read model with profile, terminal-control state,
  effective score, hard-quality gap count, and coordination-risk count.
- Replace the retired publish state name with `local_publish_ready` everywhere in
  current semantics; do not retain retired publish-state aliases.
- Project local-ci fallback owner scripts from the target repository root and
  actual `.config/ci/scripts/run-local-ci.sh` owner script.
- Harden release supply-chain evidence: checksum-pinned gitleaks install,
  current-tree plus Git-history secret scans, lockfile transitive SBOM, and
  in-toto/SLSA materials for `uv.lock` plus the SBOM digest.
- Record the archived release-adoption proposal vocabulary cleanup as part of
  this no-residue change so the repository no longer advertises the retired
  publish state as current wording.

## Capabilities

- `command-plane`: subject=fail-closed-transitions-and-publish-state; reuse=extend; change=modify; facet:lifecycle=runtime; facet:surface=cli; facet:authority=source,test,openspec
- `quality`: subject=proof-admission-report-and-supply-chain-hardening; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=ci,release; facet:authority=source,test,config,openspec,evidence

## Out Of Scope

- Remote publication or protected-branch push.
- Hosted CI success claims; local-ci remains local fallback evidence.
- Keeping old command/state/helper names as compatibility aliases.
- Host-specific assistant behavior outside repository command semantics.
