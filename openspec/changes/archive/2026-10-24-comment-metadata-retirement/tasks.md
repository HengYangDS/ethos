# Tasks

## 1. Plain Front Matter Only

- [x] 1.1 Read docs metadata from plain front matter only in the docs registry, decision records and docs health, and retire the `docs_title_not_first` gap with the comment-wrapped carrier; done when a regression proves that a comment-wrapped document under the docs root declares no metadata and reads as missing, while plain front matter keeps its meaning (`test_docs_registry_reads_no_metadata_from_a_comment_wrapper`).
- [x] 1.2 Describe plain front matter as the only carrier in `docs/governance/docs-registry.md` and record the retirement in `CHANGELOG.md`; done when neither names a compatibility reader.

## Workflow follow-up

- Prove the exact head, archive this Change, prove the archived head, then land, close out and publish.
