# Design

## Context

See the proposal for motivation. Archive resolution follows refresh and signature-repair edges.
Its repair selector currently treats every ancestor of a repair's original tip as affected, then
verifies the entire replacement mapping before checking whether that mapping contains the archive.
History repair already owns derivation of the exact affected DAG.

## Goals / Non-Goals

**Goals:** verify only real provenance dependencies while preserving fresh Git observation and
complete validation of every selected repair.

**Non-Goals:** cache Git answers across observations, weaken signature trust, change admission,
introduce a controller or alter supply and release ownership.

## Decisions

1. Reuse the native history-repair scope before demanding expensive replacement verification.
   An archive outside that scope does not depend on that repair. An ancestor-only filter cannot
   express this distinction; a claimed mapping or attestation digest cannot establish it.
2. Separate native payload-conservation observation from full signature validation in the existing
   history owner. The archive resolver uses that exact structural mapping only to find paths
   reaching current history. Derived candidate mappings live only in that observation and cannot
   grant authority: the selected chain's full validation independently rereads Git and trust.
3. Demand complete signature-owner validation for reachable candidate chains before choosing one.
   Retain observation-local verified-repair reuse and the regression that invalidates evidence
   on the next observation. Competing edges remain subject to complete validation.
4. Exercise affected and unaffected archives, reachable and unrelated replacement histories with
   a real Git DAG. Pair focused tests with the actual archive reader, ordinary status and prewrite.
5. Let fresh native parent edges derive the affected DAG. Decode correction payloads only, and
   reconstruct mappings from affected originals plus replacement-only objects. This removes repeated
   reads of conserved history at the shared owner without retaining Git answers between calls.
6. Select a refresh's exact execution branch and predecessor before decoding its complete plan.
   Keep native effect validation unchanged for selected records; unrelated inputs cannot become
   archive dependencies.
7. Use the observation's actual payload mapping to select subsequent repair edges. A selection
   needs ancestry, not a distance; native distance reads remain only where archive ordering uses
   them. Selected chains still require their independent complete trust validation.

## Risks / Trade-offs

- Scope derivation itself reads Git history. Measure the real reader before treating fewer
  signature checks as sufficient performance acceptance.
- Malformed relevant history remains untrusted; the repair selector cannot accept provenance
  from a successful scope calculation alone.

## Migration Plan

Demonstrate the old dependency-selection failure, repair the existing owner, then verify focused
tests and the actual readers. Recover the prior retained-runtime archive from native evidence
without replaying its effect. Obtain full native proof for the final signed source before archive;
prove the resulting signed archive source before governed integration. Preserve required evidence
through its native owner before lane retirement. Installed runtime promotion keeps its own gates.
