# Design

## Context

A reviewed abandonment (`ethos lane retire abandon --review-content`) snapshots every literal node
of a linked worktree (`content.py`, `reviewed_content`) and keeps the snapshot in the request's
`reviewed_content` (`contracts/retirement.py`, `_ReviewedContent.entries`). Admission and removal
verify the worktree against that snapshot (`verify_reviewed_content`, `remove_reviewed_content`),
and the terminal receipt embeds the request. The store retention design (archived `rc-plan`,
Appendix D, D.3 "Compaction") moves the nodes to one content-addressed file bound by digest; this
Change implements that part, and the retention verb that retires old records follows separately.

## Goals / Non-Goals

Goals:

- One copy of a reviewed manifest, written once, bound by digest from its request and receipt, and
  deleted when the operation is terminal and nothing else binds it.
- The same verification at admission and removal, on the same nodes.

Non-Goals:

- Rewriting or retiring the requests and receipts already written; the retention verb owns that.
- Any change to what a review observes or to the drift rules.

## Decisions

1. **The contract keeps a reference.** `_ReviewedContent` keeps `root`, `index_path` and `index`
   and replaces `entries` with `manifest`: the file's SHA-256, its size and per-root totals, which
   count the directories, files and symlinks under each top-level name and sum the file sizes from
   the node identities. A new `ReviewedManifest` model holds the nodes and keeps the tree checks;
   the reference requires the `.git` marker as exactly one file in its totals. The request digest
   binds the manifest digest, so it binds every node.
2. **The manifest is written first.** Derivation writes the manifest to
   `requests/lane-retirement-manifest/<digest>.json` with the store's content-addressed writer
   before the request is persisted, and the preview's `full_manifest` names that file.
3. **Admission and removal load it.** A new `manifest` module of the lane retirement package loads
   the file by digest, checks its size, bytes and totals, and returns the full snapshot that
   `verify_reviewed_content` and `remove_reviewed_content` already take, so verification and
   removal do not change. A missing file refuses with `lane_retirement_manifest_missing`, a wrong
   one with `lane_retirement_manifest_mismatch`; both join the receipt-invalidating gaps, whose
   continuation is the fresh content review.
4. **Terminal release.** After `persist_terminal_receipt`, under the retirement lock, the operation
   deletes its manifest unless another request in the store binds the same digest and has no
   terminal receipt. A failed deletion is reported in the result as `manifest_release` and never
   turns a terminal retirement into a failure.
5. **Inline requests continue.** A request written before this Change fails validation as
   `lane_retirement_receipt_invalid`. When its bytes verify and it carries inline nodes, recovery
   builds a coordinate view, the same request with an in-memory manifest reference that is never
   persisted or executed, and returns `fresh_retirement_command` over it, or `ethos lane status`
   when its carriers drifted.

## Risks / Trade-offs

- A second file per reviewed abandonment. The manifest is the large part, so the request and its
  receipt shrink to their coordinates.
- A manifest deleted by hand before admission blocks the receipt; the continuation is the same
  fresh review that drift selects, so nothing is removed on a guess.
- A failed derivation can leave a manifest that no request binds; the retention verb retires it as
  a manifest-only unit.
