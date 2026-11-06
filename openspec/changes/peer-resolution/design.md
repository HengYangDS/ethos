# Design

## Context

See [proposal.md](proposal.md). The reviewed drafts in
`build/runtime/work/peer-neutral-artifacts/` (draft 3 §1, draft 4 §2–§4, and both reviews of
draft 4) are the design record; this document states what the Change implements.

- `_forge_url` (`adapters/mutation/publication/retirement.py:174-180`) resolves the tracked
  `forge_repository`, then the local key, then the raw remote.
- The declaration requires both local command fields (`repository/release/publication.py:23,
88-95, 334-345`). It copies them into `topology["local"]` and counts them as owners of
  executables (`policy/references/declarations.py:355-357`).
- The fallback compares evidence with the declared verification command
  (`domain/publication/fallback.py:16-48, 121`). Publish already admits proof through
  `context.proof_admission` (`domain/publication/inspection.py:255-260`).

## Goals / Non-Goals

Goals:

- No peer coordinate or unexecuted command in tracked publication configuration.
- A rollback cannot run a predecessor on a declaration format it refuses.

Non-goals:

- The private-address class, verifier and redact verb (`private-address-records`).
- URL-bearing outputs and CI self-rendering (`peer-neutral-outputs`).

## Decisions

- **Resolver.** `forge_web_repository(root, remote)` lives in the publication adapter
  (`adapters/mutation/publication/forge.py`); `<name>` below is the peer's Git remote.
  - It reads the local `remote.<name>.forgeRepository` key first. A present but invalid key refuses
    with `forge_repository_invalid:<name>`.
  - Otherwise it uses `git remote get-url <name>` when the scheme is `http` or `https` and there is
    no userinfo, validated by the same rule. Scheme, host and port are kept; one trailing `/` and
    `.git` are stripped.
  - An http(s) URL with userinfo refuses with `forge_repository_credentialed:<name>`, never echoing
    the URL.
  - SSH and scp-like remotes report `forge_repository_unresolved:<name>`. Its next action is
    `git config --local remote.<name>.forgeRepository <web-url>`, and the review state stays
    unknown.
- **Retired fields.**
  - The loader refuses `forge_repository`, `local_verification_command` and
    `local_installation_command` with `publication_declaration_field_retired:<field>`.
  - A paradigm obligation reports the same fields. Like every paradigm gap, it blocks prove, land
    and publish, and never `status`, `lane start`, prewrite, `repair-paradigm` or commit.
  - The repair is pure: `_restated_field` with `_RETIRED_FIELDS` for the commands, and a peer
    handler for `forge_repository`. It masks only `forge_repository` lines in `_edit_view`, drops
    `patch` from its result, and reports only the field and the peer.
  - An absent `[publication]` table is admitted as zero peers.
  - `declarations.py` stops counting the local commands as owners.
- **Fallback.**
  - `local_ci_fallback` projects `context.proof_admission`: `admitted`, `missing`, `unavailable`,
    and `not_required` for review roles. Each state has text.
  - The prove continuation gains `--full`.
  - `inspection.py` prefers the audit's repair action, then the proof continuation, on both the
    readiness path and the `--ref` path.
  - `local_ci` (session, tool and evidence reader) retires, and `topology["local"]` goes.
- **Rollback.**
  - The hook activation preflight runs only when `--runtime` names a build other than the invoking
    one. It sits between `hook/activation.py:78` and `:83`, before materialization pins anything.
  - It probes `<target python> -m ethos.cli publish --root <root> --json`. It refuses only on
    `publication_topology_declaration_invalid`, as `runtime_rollback_declaration_repaired`, and
    requires the root's HEAD to contain the accepted tip.
  - The refusal emits the exact gap and the action "restore the predecessor's declaration in a
    lane".
  - A probe that fails blocks with its own gap.
  - Restoring is a new Change that restores the predecessor's tables, lock entries and command
    fields from the pre-repair commit, never `forge_repository`, and leaves archives alone.
  - The supported rollback runs the CURRENT console:
    `"$(sed -n 2p <common>/ethos/runtime/CURRENT)/python/bin/ethos" hook install --root <lane>
--runtime "$(sed -n 2p <common>/ethos/runtime/ROLLBACK)" --json`.
  - `status` names that command, with the root, whenever a ROLLBACK runtime is held. The
    preflight, not status, decides whether the tree's declaration admits it, so status needs no
    second oracle for the predecessor's format.
- **Cutover.**
  - ETHOS goes predecessor first:
    1. repair in the lane with the lane's own `python -m ethos.cli`;
    2. commit and prove;
    3. push the proposal from the unrepaired canonical root with a raw
       `git push <peer> <lane-oid>:refs/heads/proposal/<topic>` under pre-push admission, which is
       a stated exception to the command plane's publish rule;
    4. land, run `ethos hook install`, then publish.
  - Adopters go successor first:
    1. in the lane, bind the release, `mise install --locked`, `hook install`;
    2. repair and prove;
    3. push the proposal from the lane;
    4. land, publish from the canonical root, and retire.
- **Hosted smoke.**
  - The retained predecessor fixture keeps the old fields until no predecessor needs them.
  - The repair runs at the end of `prove_retained_authoring`, which asserts only retired-field gaps.
  - Until the refused-rollback journey leg ships, the upgrade receipt declares "rollback after
    declaration repair" as a limit.

## Risks / Trade-offs

- **Two runtimes, two formats.** Each refuses the other's declaration. Before landing, these checks
  pass:
  - a proposal push from an unrepaired root under the predecessor passes;
  - publishing between landing and `hook install` refuses;
  - publishing after `hook install` passes;
  - both runtimes' plans are compared.
- **A predecessor-coordinated `hook install`** skips re-execution, so it cannot be refused. Its
  loader still fails closed at publish.
