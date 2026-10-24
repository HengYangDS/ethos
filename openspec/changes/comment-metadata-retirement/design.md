# Design

## Context

Documents under the profile docs root declare their metadata in plain YAML front matter. A compatibility path also accepts the same payload wrapped in a leading HTML comment, so that a forge renders the title first. `front_matter(..., allow_html_comment=True)` reads that wrapper, and the registry and the repository audit select it. Docs health then requires the title to be the first visible block (`docs_title_not_first`), and decision-record rationale checks skip the wrapper's HTML block. The repository paradigm separately reports a wrapper and removes it with `ethos lane repair-paradigm --apply`.

## Goals / Non-Goals

**Goals:**

- Plain front matter is the only metadata carrier the registry, the repository audit, docs health and decision records read.
- A wrapped document declares no metadata and reads as missing, as the accepted requirement already states.

**Non-Goals:**

- Changing the paradigm's report and repair of a wrapper, or any OpenSpec, Skills or system-axiom syntax.
- Migrating adopters. No governed repository tracks a wrapped document now.

## Decisions

- **Remove the carrier at its one reader.** `front_matter` loses its `allow_html_comment` mode, so every consumer reads the same plain form. Keeping the parameter with a refusing default was rejected: it would leave a second, unused carrier for a later caller to select.
- **Retire the dependent checks with the carrier.** The title-first rule and the decision-record skip existed only for the wrapper, so `docs_title_not_first` and the HTML-block skip go with it.
- **Let the existing missing-metadata report speak.** A wrapped document then reaches the registry's existing missing-metadata path. No new gap code is added.

## Risks / Trade-offs

- [A repository outside the governed fleet still wraps its metadata] → Its documents read as missing metadata and block. The paradigm report names each wrapper, and its repair removes it.
- [A forge renders front matter above the title] → This is the accepted trade-off of a single plain carrier.
