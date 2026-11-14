# Design

## Context

See the [proposal](proposal.md). Today a job binds trust with
`python -B -m tools.ci.toolchain.commit_trust`, whose `main` reads `ETHOS_COMMIT_TRUST_ANCHOR` and
`ETHOS_COMMIT_ALLOWED_SIGNERS` and calls `bind_commit_trust` or `bind_commit_trust_material` in
`tools/ci/toolchain/environment.py`. The validation is already product code:
`ethos.adapters.repo.trust_anchor.verification.trust_anchor` refuses an anchor that is missing,
relative, inside the checkout or writable by an untrusted identity, and
`ethos.adapters.repo.trust_anchor.filesystem.protect_for_current_identity` protects a created file.
Only the selection of the input and the local `git config` write with its read-back live in
`tools/`, which no release ships. The model `.config/ci/pipeline.cue` calls the module from the
shared bootstrap of both forges and from the release legs.

## Goals / Non-Goals

Goals:

- A released command binds operator-supplied commit trust, so a CI job of any adopter needs no
  ETHOS source checkout for it.
- ETHOS's own pipelines use that command, and the private path goes.
- The inputs, the effect and every reachable gap name stay as they are today.

Non-Goals:

- Any change to `ethos hook commit-range`, to signature verification or to the anchor rules.
- Adopters' CI templates and the migration of the Python service, which later Changes and that
  repository's own lane carry.
- Creating keys, discovering signers or reading trust from the candidate.

## Decisions

1. **A separate operation, `ethos hook bind-trust`.** `hook commit-range` stays read-only, and one
   operation serves GitHub and GitLab jobs alike. The name is a verb and its object, as
   `hook retire-supply` and `hook retire-records` are.
2. **Preview and apply are two catalog entries**, declared with `modes()` as the group's other
   pairs are: `hook.bind-trust.preview` reads, and `hook.bind-trust.apply` adds `local-write` under
   the authorization kind `apply` and exits by its verdict. The preview also exits by its verdict,
   as the group's other previews do, so a refused input fails a job that only previews. The
   temporary anchor of the material input lies outside the checkout; the entry stays `local-write`,
   as `lane trust-commit-signer`, which rewrites the external anchor, is.
3. **The body is born in the application package**, in `src/ethos/application/hook/commit_trust.py`,
   under the control fence's existing `src/ethos/application/hook/` prefix. It calls the two
   adapter owners and adds nothing to them, so the import closure of the Git hook path
   (`ethos.adapters.repo.hook.protocol`) is unchanged.
4. **One input, three sources.** `--anchor <path>` and `ETHOS_COMMIT_TRUST_ANCHOR` name a protected
   file; `ETHOS_COMMIT_ALLOWED_SIGNERS` carries public material. More than one refuses with
   `ci_commit_trust_inputs_ambiguous`. None passes with the state `unbound`, since a job without an
   operator input binds nothing and commit verification still refuses a missing required anchor.
5. **The preview writes nothing.** For a file it validates the anchor and names it; for material it
   checks only that the material is not blank, since naming a file would mean creating it. Its next
   step is the exact apply request.
6. **The apply writes one setting and reads it back.** It writes the local
   `gpg.ssh.allowedSignersFile` and refuses with `ci_commit_trust_projection_failed` unless the
   read-back names the anchor. Material goes into a new protected directory under the temporary
   root first; a refusal or a failed write removes that directory. A failed protection is a refusal
   with the host's bounded reason, not a traceback.
7. **Results, not exceptions.** The private module raised `ValueError`; the operation returns a
   result whose `summary` names the supplied input and the anchor's path, never the material.
8. **The pipeline spells the call once.** `pipeline.cue` gains one `let` for the invocation, used
   by the shared bootstrap and by the release legs, and both projections are regenerated.

## Risks / Trade-offs

- A caller that imports `tools.ci.toolchain.commit_trust`, or the two helpers, from an ETHOS source
  checkout fails at import once it moves to this commit. Only source importers are affected: one
  Python service, which moves to the released operation in its own lane. No released package ever
  shipped `tools/`.
- The gap `ci_commit_trust_anchor_unresolved` is not carried over. It was unreachable: the anchor
  owner returns no anchor only together with a gap.
- The apply always writes the setting, where the module skipped a write that would not change it.
  Git writes the same bytes, so the configuration is unchanged.
- A job log now holds the result's JSON with the anchor's path. The path of a temporary file is not
  secret, and the public material is never printed.
- The move costs more product lines than it frees in `tools/`, because the released operation adds
  a preview, a flag, a structured result and its next step.
