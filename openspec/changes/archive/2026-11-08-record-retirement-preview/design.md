# Design

## Context

Store retention (archived `rc-plan`, Appendix D, with `design-draft3.md` and its decision of
2026-11-07) retires store records through one verb with a write-ahead plan; the compaction of
reviewed manifests landed as `retirement-manifest-compaction`. Four writers put content-addressed
artifacts in `artifacts/`: proof-check documents (`adapters/mutation/proof_artifacts.py`), merge
preimages (`adapters/repo/merge/recovery.py`), native attempt archives
(`adapters/gates/native/attempt.py`) and JavaScript attempt archives
(`adapters/gates/javascript/execution.py`). Lane retirement keeps requests, progress snapshots,
manifests and terminal receipts in the store's `requests`, `operations` and `receipts` trees.

## Goals / Non-Goals

Goals:

- A preview that names every candidate record and its bytes, keeps everything any kept record or
  the accepted tree names, and writes the plan that the later apply will execute.
- The age floors and decoding bounds as declared parameters.

Non-Goals:

- Deletion, the apply's locks and tombstones, and `ethos status` reporting, which follow as their
  own Changes; publication requests and superseded lane retirement units, which join the apply.
- Custody, runtimes, packages, hooks, tool caches and payload detail, which keep their owners.

## Decisions

1. **One operation, one verb.** `preview_record_retirement` in `ethos.application.retention`
   orchestrates; `ethos.adapters.store.retention` holds the kinds, the roots scan and the plan; the
   hidden `hook` group's `retire-records` calls the operation. The preview's step is
   `local-evidence-write`, since it writes only its plan.
2. **Admission.** The invoking interpreter and build must be the selected runtime's, compared as
   the runtime binding compares them; the floors come from the accepted branch's binding blob read
   with `git show`, an absent blob declaring nothing; the preview refuses while the repository's
   proof slot is held, taking the slot lock without blocking.
3. **Kinds are writer schemas.** A JSON artifact is a proof-check document when it has
   `schema_version` 1, `head` and `checks`, and a merge preimage when its keys are `observation`,
   `files`, `stage_blobs` and `metadata`; an archive is a native attempt when it holds
   `execution.json`, `stdout.txt` and `stderr.txt`, and a JavaScript attempt when it holds
   `observation.json`. A lane retirement unit groups a request, its manifest, its progress
   snapshots and its terminal receipt; it is `terminal` with a receipt, `receipt-only` when a
   receipt names a request that the store no longer holds, and `manifest-only` when no request
   binds a manifest. Units without a receipt otherwise stay unclassified and kept.
4. **Roots over-approximate.** Every 64-hex token in a kept store file outside `runtime`,
   `packages`, `hooks`, `tool-cache` and `cache`, in a live Attestation member, in a reached item
   or in a file of the accepted tree is a root; the scan reads zip, gzip and tar members and decodes
   base64 runs, to `retention.decode_depth` levels and `retention.decode_bytes` per carrier, and a
   kept carrier it cannot read refuses the preview. A mistaken match only keeps.
5. **Selection and plan.** An item is a candidate when its kind is owned, none of its tokens is a
   root, and its newest file is older than its floor: `retention.grace_seconds` for artifacts and
   `retention.record_seconds` for lane retirement units. The plan
   `requests/record-retirement/<digest>.json` keeps the accepted commit, the cutoffs and each
   candidate's kind, state, paths, sizes and mtimes; it is content-addressed, so a repeated preview
   of an unchanged store writes the same plan.
6. **Floors and refresh.** A parameter row marked `floor` applies a higher value within its bound
   without a reason and treats a lower one as a gap; units gain `bytes` and `levels`. An identical
   content-addressed write refreshes the existing file's mtime, so a re-adopted record is young.

## Risks / Trade-offs

- The roots scan reads every kept file and is slow on a large store; it is a manual preview, and
  bounding it by token search keeps memory to one carrier at a time.
- Over-approximation keeps more than strictly needed; a later reader of an encoded mention stays
  correct.
- Running only under the selected runtime means a lane cannot preview its own store with lane code;
  the lane's tests cover the logic on fixture stores.
