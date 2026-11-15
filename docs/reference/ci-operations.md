---
subject: ethos:ci-operations
role: reference
state: active
relations:
  part_of: command-plane.md
---

# CI Operations

This reference answers one reader question: what does a repository declare for its CI, and what
does a CI job run to observe a ref update? It is part of the command reference: the
[Command Plane](command-plane.md) lists the public commands and their result, and its section on
[commit integrity](command-plane.md#commit-integrity-and-accepted-history-repair) describes the
trust binding that a job runs before `ethos hook commit-range`.

## Native CI Projection

`ethos lane project --json` previews every declared output as one exact patch;
`--check` refuses drift without writes. Apply that patch with `--patch <file>
--apply --authorize --expect-head <head>` under current Work Lane admission.

Declare `schema = "ethos-ci-template-consistency-v1"` in
`.config/checks/ci-projection/policy.toml`, with a real CUE `compiler.source`,
typed TOML/JSON `compiler.inputs` and `compiler.common = ".config/ci/verification.cue"`.
The installed model/compiler are not repository source members. Keep parameters in `.config/ci/`
and supplied executables/Forge references in `.config/ci/runners.toml`. Each provider workflow
has SourceContracts binding its declaration, output group and integrity gate; common jobs invoke
`mise exec --locked -- ethos`. The repository binds public `http:ethos` supply and platform locks.
That declaration puts only the `ethos` console on `PATH`.

GitLab `runners.<name>.preparation` precedes locked installation; `supply.checks.github`
and `supply.checks.gitlab` follow it. `evidence_paths` under `build/evidence/` retain additional
reports. Common and runner `variables` cannot replace `GIT_DEPTH = "0"`; preparation cannot
replace shared proof, trust partitions or source timeout. GitLab `offline_candidate_variable`
defaults to `ETHOS_OFFLINE_CANDIDATE`, accepting an existing repository name. Selected candidates
admit only protected accepted/release API/web requests and exclude source jobs. Retain additive
GitLab offline jobs and a separate GitHub offline workflow. Their deadlines, release validation,
acquisition/checksums, cold payload, peer-outage and hosted qualification retain existing owners.

## Exact Ref Observation For CI

```bash
ethos hook ref-update --target-ref <full-ref> --proposed-head <object-oid> --remote-head <old-object-oid> --remote <name> --root <repository> --json
```

Use the repository-native zero OID for a new ref and `--trusted-baseline <oid>`
when no declared accepted tracking ref supplies the baseline. Both SHA-1 and
SHA-256 coordinates are supported. The command observes the exact introduced
commit range, prior target policy and proposed OpenSpec tree without a host
Lease, proof issuance, local ref changes or remote effects. Deletion has no
introduced range; observation alone never authorizes deletion.

Review targets may carry unfinished intent. Accepted/release targets cannot
use detached checkout identity or a changed candidate declaration to evade
their stronger obligations. Results include `boundary`, `why`, exact coordinates
and a single diagnostic `next_action`; CI consumes the result rather than
copying a parser. For publication effects use the guarded `publish` surface.
