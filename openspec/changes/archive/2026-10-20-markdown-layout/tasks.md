# Tasks

## 1. Layout

- [x] 1.1 Report each authored Markdown document whose blank lines differ from its parsed structure as one `markdown-layout` gap, exempting received documents and immutable roots; done when the conforming, separator, literal, received and empty-document regressions in `tests/unit/repository/test_paradigm_markdown.py` pass.
- [x] 1.2 Repair the gap through `ethos lane repair-paradigm` by changing only blank lines, and keep it report-only when the structure would change; done when every separator case lays out to its expected text and the structure case stays report-only.

## 2. Conformance

- [x] 2.1 Lay out ETHOS's own documents with `ethos lane repair-paradigm --apply`; done when the repository audit reports no `markdown-layout` gap.

## 3. Documentation

- [x] 3.1 Record the layout in DR-0012 and the changelog; done when the documentation checks pass.

## Workflow follow-up

- Prove the exact head, archive this Change, prove the archived head, then land, close out and publish to both peers.
- Adopters conform in their runtime-rebind batches, held by their current owners: web-ingestion-benchmark, ethos-introduction-film, ddwg-introduction-film and data-department-work-guidelines.
