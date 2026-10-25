# Design

## Context

The existing acceptance owns a predecessor, successor, rollback and reactivation journey. Its
brownfield snapshot records common configuration, schema, Lease rows and one checkout's files
and status. Git indexes and linked checkouts are independent state with legitimate staged-only
changes. Existing native Git index identity already captures modes, object IDs and conflict stages.

## Goals / Non-Goals

**Goals:** preserve complete authored state across the existing normal upgrade journey, and make
undetected damage falsifiable through focused regressions and exact-package execution.

**Non-Goals:** change activation policy, cache authorization, introduce a migration controller,
modify archived intent, qualify interruption or uninstall, or activate adopters.

## Decisions

1. Extend the existing immutable `RetainedRepository` snapshot. Reuse the native index-content
   identity; keep missing files and filesystem modes explicit. Observe each registered linked
   checkout through the same snapshot, with native registration binding. A second preservation
   registry or controller would duplicate Git and the current acceptance owner.
2. Seed one real leased fixture lane through native Git, with different staged and working bytes,
   deletion and untracked content. Keep the accepted fixture intact. The existing package attempt
   owns fixture cleanup; the real adopter's dirty work is never the test input.
3. Retain phase-specific failure reasons and compare the same complete prestate after upgrade,
   rollback and reactivation. Project the additional evidence from that snapshot rather than
   re-observing or copying policy into the receipt renderer.
4. Move the existing retained-upgrade tests to their own semantic pytest home and add independent
   staged-only, mode and linked-worktree faults. Do not duplicate the lifecycle tests or split
   production ownership merely to satisfy a line ceiling.

## Risks / Trade-offs

- Package qualification remains distinct from unit acceptance. A missing predecessor or failed
  dependency audit cannot be reported as a qualified cutover.
- Filesystem modes vary by platform. Native index modes are always observed; POSIX permission
  regressions declare their platform boundary, without skipping the index obligation elsewhere.
- Missing or changing worktrees fail observation. No pruning, reset or cleanup repairs the fixture
  by discarding evidence.

## Migration Plan

First demonstrate the old blind spots, then extend the existing owner and exercise its direct
consumers. Freeze signed source and execute its declared proof and exact-package predecessor
journey. Adopter installation follows only qualified evidence and native authorization.
