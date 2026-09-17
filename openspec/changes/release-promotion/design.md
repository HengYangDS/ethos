## Context

Accepted and release source are different refs, not different authorities over
product content. Shipping exact accepted source preserves its objects and
historical attribution; it cannot retroactively claim pre-adoption signatures.

## Goals / Non-Goals

- Add explicit release selection to existing land with exact source/prior ref
  coordinates, current proof, accepted effect and native ref intent.
- Create requested signed annotated tags from committed native version inputs.
- Distinguish contribution admission, local selection, peer publication, hosted
  verification and deployment.
- No caller policy override, grandfather list, extra lifecycle or history rewrite.

## Decisions

1. One existing GitEffect updates the independent release ref, optionally
   creates a tag and asserts accepted. Existing intents, CAS, observation and
   Attestation own the effect.
2. Accepted-content reuse requires exact current accepted source, a validated
   accepted effect and current repository-transition proof. It never labels
   unsigned history signed. Ordinary contribution admission remains unchanged.
3. Native Git prepares signed tag bytes in an owned isolated object context;
   the original receives that exact object without a speculative tag ref.
   Repeated requests recognize the prior exact tag/effect instead of resigning.
   An owned native bare store retains tag bytes through plan persistence; one
   stable request-directory lock fences cooperating writers. A signing attempt
   without a resulting native tag is UNKNOWN and never automatically repeated.
4. The release identity owner observes committed VERSION, package.json or static
   pyproject project version. A unique native value is required; malformed or
   conflicting sources fail closed instead of silently choosing a filename.
5. Local independent main/tag movements require matching executor intents, not
   the former permissive fallback. Linked release worktrees are checked before
   CAS and synchronized through the existing worktree owner after it.
6. Historical evidence does not grant current effect authority. Recovery
   reobserves refs, coordination and trust; file sync and multi-peer publication
   are not falsely described as one atomic Git transaction. Exact inverse admission
   requires the committed forward intent and the same plan. Saved plans bind
   the actor and are compared with fresh compilation before execution.

## Validation

Native signed fixtures cover SHA-1/SHA-256, release without tag, package-native
tag, missing proof/acceptance, stale accepted/main, dirty linked content,
conflicting versions, untrusted/divergent tags, repeated and interrupted effects,
and independent peers. Preserve unsigned pre-adoption ancestors while rejecting
unaccepted sources and invalid new contributions. Compare all refs and content
before and after rejection.

## Risks

Hashes and self-described receipts do not establish acceptance. Reuse must
consume existing validators and exact current source. Unknown effects require
observation before replay. Version discovery must reject ambiguity.
