## ADDED Requirements

### Requirement: Markdown layout follows parsed structure

Every authored Markdown document SHALL separate adjacent blocks and leading front matter with one blank line, keep reference definitions together, keep a one-block list item tight with the next item and separate any other item's blocks and its next item with one blank line, without repeated blank lines or edge padding. Quotes, tables, literal blocks and the node after a formatter-ignore comment keep their bytes; received documents and immutable roots are exempt.

#### Scenario: A blank line follows a one-block list item

- **WHEN** a Changelog list leaves a blank line after a one-paragraph item
- **THEN** the paradigm reports the document's Markdown layout, and `ethos lane repair-paradigm --apply` removes only that blank line.

#### Scenario: A heading touches its text

- **WHEN** a main spec carries `## Purpose` directly followed by its paragraph
- **THEN** the paradigm reports the document, and the repair inserts one blank line.

#### Scenario: A multi-block item touches the next item

- **WHEN** a list item's two paragraphs are separated but the next item follows without a blank line
- **THEN** the repair separates them with one blank line.

#### Scenario: A code block holds blank lines

- **WHEN** a fenced code block holds two consecutive blank lines
- **THEN** the paradigm reports no Markdown layout gap.

#### Scenario: A received transcript keeps its bytes

- **WHEN** Git attributes mark a verbatim transcript `linguist-vendored`
- **THEN** the paradigm does not lay it out.

#### Scenario: A repair would change the structure

- **WHEN** dropping blank lines before a document's YAML-like block would turn it into front matter
- **THEN** the gap stays report-only.

## MODIFIED Requirements

### Requirement: Formatter inputs respect declared carrier ownership

A formatter's declared inputs SHALL exclude carriers that already have another declared owner, such as official OpenSpec artifacts. Those carriers SHALL keep their own owner and checks, and their Markdown layout SHALL still follow parsed structure.

#### Scenario: A carrier has an official owner

- **WHEN** a repository declares its OpenSpec artifacts official-owner-only
- **THEN** the Markdown formatter's inputs exclude them, their own checks still run, and the paradigm still reports their Markdown layout.
