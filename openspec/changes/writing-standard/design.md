# Design

## Context

See the [proposal](proposal.md). The contract stands at 500 non-blank lines, the document
ceiling, measured with the product's own rule on 2026-11-22. The definition is 301 words. Its
source is a file outside this repository, so no test here can read it.

## Goals / Non-Goals

Goals:

- One place in this repository holds the definition, in its owner's words.
- A changed word in that copy fails a test.
- The contract and every other carrier point at that place.

Non-Goals:

- A check that judges prose against the standard. The standard is applied by a reader.
- A change to the four reported places in contract text.

## Decisions

1. **The definition has a document of its own, and the contract cites it.**
   - **Rests on:** the ceiling: a copy inside the contract would make 523 lines. The owner asked
     for a citation and no wording per carrier.
   - **Considered:** the block inside the contract; a link to the shared rules, which no reader
     of this repository can follow.
   - **Chosen because:** the contract stays at its ceiling, and a reader finds the whole
     definition one link away.
   - **Applies to:** `docs/governance/writing-standard.md`, the governance index and the
     contract's paragraph on public prose.
2. **The copy is pinned by the digest of its words.**
   - **Rests on:** the repository wraps Markdown at 100 columns and the source wraps wider, so
     the bytes differ while the words are the same.
   - **Considered:** a second copy of the text in the test; a digest of the bytes.
   - **Chosen because:** a digest of the words with every whitespace run as one space admits a
     new wrap and refuses a changed word, and the test holds no second text.
   - **Applies to:** `tests/architecture/test_product_design_contract.py`.
3. **The contract keeps one clause of its former sentence.**
   - **Rests on:** "visual appeal never permits a second ontology or an unverified completion
     claim" is a rule of the contract and no gloss of the standard.
   - **Considered:** dropping the whole sentence.
   - **Chosen because:** the rule has no other carrier.
   - **Applies to:** the contract's paragraph on public prose.
4. **Each purpose line is written from its own document.**
   - **Rests on:** four documents ended with the same sentence, which fits any document.
   - **Considered:** removing the line.
   - **Chosen because:** the documents' form carries a purpose line, and each document has a
     purpose that its own first paragraphs state.
   - **Applies to:** the four documents named in the tasks.
5. **The long paragraph is divided without a changed word.**
   - **Rests on:** a comparison of the document's words before and after by program: equal apart
     from the two semicolons and the purpose line.
   - **Considered:** rewriting the passage.
   - **Chosen because:** the fault is the missing breaks; the sentences are sound.
   - **Applies to:** `docs/architecture/runner-and-mutation.md`.

## Risks / Trade-offs

- The pin fails when the owner changes the definition at its source and this copy follows. That
  is its purpose: the digest is then taken again from the source with the copy.
- The standard's document names where it comes from and cannot link to it. A reader outside the
  owner's workstation takes the copy on trust; the test guards the copy, not the source.
