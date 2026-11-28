# Design

## Context

See the [proposal](proposal.md). The re-creation reads a completed repair from the attestation set
in the repository's common directory, maps the tag's target through it, signs a tag object on the
mapped commit and moves the tag ref under a Git effect plan. The plan's pre-state includes the
asking checkout's head, tree and repository profile. Before this Change the apply's pre-state also
required that head to be the mapped commit; that equality was the only condition that tied the
asking checkout to the repaired line.

## Goals / Non-Goals

**Goals:** the three items of the [proposal](proposal.md)'s What Changes: a tag re-created from the
accepted branch's head as well as from its mapped commit, under one plan for the preview and the
apply; a batch over tags on different commits under one plan digest; an unborn checkout refused at
the preview.

**Non-Goals:** where a tag lands. The completed repair's mapping, the signature and the request
decide it, as before; the section What does not change below lists what stays.

## Decisions

1. **The asking checkout stands on the repaired line.** Its head is either the mapped commit, as
   before, or the accepted branch's head with the mapped commit among its ancestors. The accepted
   branch is the one that the checkout's working-tree release binding names, which must agree with
   the binding committed at that branch's head. The check compares commits, not branches: a linked
   or detached checkout whose head is the accepted head's commit is admitted, and so is a Work Lane
   with no commits of its own. A Work Lane with commits of its own, a detached head elsewhere and
   an unborn checkout refuse with `release_retag_checkout_unrelated`. The refusal is per tag, like
   the plan's other per-tag refusals (`release_retag_original_missing`,
   `release_retag_name_occupied`, `release_retag_target_not_mapped`,
   `release_retag_signer_untrusted`), which return a refusal rather than raise, and none of which
   has a row in the gap registry.
2. **One plan for a batch.** From the accepted head, tags whose targets map to different commits
   are planned together under one plan digest. Each ref moves by exact compare-and-swap from its
   current value (the original tag object, or absent when the original was deleted locally and
   restored from the repair's bundle) to the re-created object.

A mapping is found only below the accepted head, so its mapped commit is below that head whenever
the mapping is found; the ancestry check in decision 1 holds in that case and guards the rule if
the mapping's source changes.

## What the plan now records

The plan's head, tree and repository facts are the asking checkout's. From the accepted head, the
receipt's facts and plan digests and the ref intent's plan digest are computed from the accepted
head and its tree, and the effect record's plan, input, output and freshness name them as the
pre-state of the tag move, where before they named the tag's mapped commit. The repository fact is
the profile committed at the asking head, so from the accepted head that profile must be valid under
the current schema and carry the same `profile_id` as the tags' commits. The tag object and its
destination are the same from either place.

## What does not change

- The request file under the common directory binds no checkout, head, actor or expiry, and the
  apply re-plans rather than consuming the preview. The digest that carries forward covers only the
  re-created object ids, not the expected values and not the checkout. A preview from one admitted
  place for a tag can therefore be applied from the other; both pass decision 1, and the
  destination is the same.
- A raw `git update-ref` of a planned tag move is still refused for want of an intent.
- The hook that judges the tag move reads the plan and the mapping, never the checkout's head.

## Behaviour that changes

- A batch over tags on different commits now completes from the accepted head. From one tag's
  mapped commit, the other tags refuse with `release_retag_checkout_unrelated` before any ref
  moves. Before, the batch moved and receipted the first tag and then raised
  `git_effect_plan_prestate_stale` on the next, leaving it half done.
- In a repository whose accepted branch still has its legacy name, the standard accepted ref is
  missing and the pre-state identity reads the role table committed at the asking head. From the
  accepted head that is the accepted line's current table, where before it was the table at the
  mapped commit.

## Reach

- A linked Work Lane whose head holds commits of its own is refused (decision 1), unless its
  binding names its own branch as accepted (next item). Before this Change it was refused by the
  head equality.
- A checkout of a branch whose binding names that branch as accepted is admitted at that branch's
  tip when the mapped commit lies beneath it, because the mapping is resolved below the head that
  the binding names. The tag lands on the same mapped commit as from the true accepted head, since
  the mapping comes from the completed repair; the records name that branch's tip (see "What the
  plan now records"). If the mapped commit is not beneath it, the tag refuses: with
  `release_retag_target_not_mapped` when no mapping is found below that tip, otherwise with
  `release_retag_checkout_unrelated`. Before this Change the same checkout reached the same mapping
  from the mapped commit with one uncommitted edit of the binding, so the Change does not create
  this reach.
- A repair is validated by its source commit's own binding and its observed effect
  (`completed_signature_repair`); whether its replacement lies beneath the accepted line is decided
  only by the head that the binding names. After two repairs in a row, a branch that names itself
  accepted and still holds the first repair's history maps a tag onto that first replacement,
  which the true accepted head no longer contains; from the true accepted head the two mappings
  compose and the tag lands on the current line. The same mapping was reached before this Change
  from that commit with one uncommitted edit of the binding.

## Risks / Trade-offs

- A reader of the effect record that expects the mapped commit as the pre-state now sees the
  accepted head. No reader of these facts exists in the product: publication of a re-created tag
  reads the receipt's body and qualifies the tag by its original release record's proof, which
  this Change does not touch. A tool outside the product that reads the effect record would see the
  accepted head.
