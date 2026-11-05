# Tasks

## 1. Re-tag

- [x] 1.1 Re-create a mapped release tag on its replacement commit. Done when a repaired fixture's
      tag is re-created with the original header and message, only target and signature changed,
      and one receipt binds both objects, the mapping attestation and the mapped target; the test
      fails first. The test preceded `retag.py` and failed on its import at `a07259539`; it now
      passes through `land --retag`, restoring the pruned original from the repair's bundle.
- [x] 1.2 Refuse each failing tag by name. Done when an unmapped target, an unverifiable mapping, a
      missing original, an occupied name, a stale plan digest and an untrusted signer each refuse by
      name without moving a ref, and a mixed batch names only the failing tag; mutation checks kill
      each rule. All six refusals pass, the mixed batch names only `v0.9.0`, and 11 of 11 mutants
      are killed, including the hook's planned move, the receipt's mapping binding and its lineage.
- [x] 1.3 Expose `ethos land --retag`. Done when the CLI previews and applies a batch with
      `--expect-plan-digest`, and the command reference documents it. The re-creation test drives
      both through the CLI, and `docs/reference/command-plane.md` documents them.

## 2. Publication

- [x] 2.1 Publish a re-created tag on the original qualification. Done when a re-created tag
      publishes under a later policy on the original release record's proof after that proof's set
      member ended, and the same tag without its receipt is judged under the current policy and
      refuses. Both hold in one test, which also refuses forged mappings and any unplanned tag move
      in the hook. Over `fa4f841e2` the affected suites pass 233 of 233.

## 3. Rule owners

- [x] 3.1 Record the `repository-governance` requirement and the changelog. Done when strict
      validation, the archive simulation and `changelog_errors` pass. Both archives simulate in
      order with 12 of 12 specs valid, and `changelog_errors` reports nothing before and after the
      `### Added` entry.
