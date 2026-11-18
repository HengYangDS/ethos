# Proposal

## Why

The gate asks that every refusal carries its bound next step. Six refusals of lane verbs do not,
each met by a session between 2026-11-14 and 2026-11-15:

- `lease_actor_mismatch` at a landing names no handoff. The landing owner of a governed repository
  could not land a lane that another session had started and proved; the native replacement of
  the holder is `ethos lane handoff`.
- A prewrite for a Change's own files answered `openspec_material_path_uncovered:<path>` with the
  next action `ethos status --json`. The cause, a proposal without its `Impact` heading, was only
  in the expanded detail: an invalid Change is not selected, so each of its paths reads as
  uncovered.
- A prewrite under a Change that held a proposal and tasks and no design answered
  `openspec_status_incomplete:<change>`, and its OpenSpec detail was empty. It did not name the
  missing artifact.
- `ethos hook install --runtime <installation id>` answers
  `hook_install_failed:hook_runtime_current_target_invalid` with a next action that drops
  `--runtime`. It does not say which condition failed: a relative path, a redirected path or a
  name that is no digest.
- A first CI projection needs two commits in a fixed order. One commit with every declaration is
  refused for the missing generated pipelines, and a projection before any commit is refused
  because references are admitted only from the committed runner declaration. Each refusal is
  right alone; together they name no path.
- A repository that adds a peer cannot publish a proposal ref to it before the peer has an
  accepted branch. The refusal does not say that the peer joins at the landing and that review
  runs on the existing peer.

Two further gaps of lane verbs were met on 2026-11-18. They are of another kind and stand here so
that the row's design places them:

- No command retires a draft. A prewrite under the draft's own selector refuses the removal of
  its files with `openspec_requested_change_missing`, and under another Change the paths do not
  match (`openspec_change_path_mismatch`). A draft whose matter is done stays in the tree with a
  note.
- Relayed by a governed repository's session and not yet measured here: the preview of
  `ethos lane archive-change` passed while three repository files still linked the Change's old
  directory, and the proof's link gate failed after the archive.

## What Changes

- The first gap of a refusal is its cause, and its next action is the step that removes it: the
  handoff, the missing heading or artifact, the accepted form of the runtime argument, the commit
  that the projection waits for, the landing that admits the peer.
- A regression for each of the six.
- The design says where the two further gaps go: into this row, or into rows of their own.
- Carried from `environment-entry`: no continuation renders `--holder-ref`, because a lane verb
  takes its holder from the invocation's actor, and the flag stays accepted for one support window.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

The results of `lane prewrite`, `land`, `hook install`, `lane project` and `publish`. Exit codes
that this row changes are a Breaking entry of its release.

Owner: the release lead. Next action: converge the design and measure the patch. Read again: at
the cut of 0.2.0-beta.14.
