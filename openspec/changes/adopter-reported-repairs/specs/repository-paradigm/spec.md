## MODIFIED Requirements

### Requirement: Code files stay within the common size ceiling

Every tracked file of a registry language SHALL have at most `code_effective_lines` effective lines,
the lines that hold a token that is not whitespace, a comment or documentation, unless Git
attributes mark it vendored or generated or it is a declared byte-bound carrier. The contract SHALL
hold a default of 500 and a bound of 1000 for both per-file ceilings. A binding MAY declare one
whole-tree value in `.ethos/rules.toml` `[paradigm.size]`; an invalid one SHALL leave the default in
force.

#### Scenario: A Python file outgrows the ceiling

- **WHEN** a governed repository that declares no code ceiling tracks a Python file with 501
  effective lines
- **THEN** the paradigm reports the file and the 500-line ceiling.

#### Scenario: A file in another language outgrows the ceiling

- **WHEN** a governed repository that declares no code ceiling tracks a Go, Rust or JavaScript file
  with 501 effective lines
- **THEN** the paradigm reports the file and the 500-line ceiling.

#### Scenario: Comments and documentation do not count

- **WHEN** a tracked Rust file holds 450 lines of code, 20 attribute lines and 100 lines of `///`
  documentation and `//` comments
- **THEN** it has 470 effective lines and passes the default ceiling.

#### Scenario: The registry decides what is code

- **WHEN** a repository tracks TOML, JSON, YAML, CUE and Markdown files with 800 lines each
- **THEN** the code ceiling measures none of them.

#### Scenario: A received file is not measured

- **WHEN** the repository's `.gitattributes` marks a tracked JavaScript file with 900 effective
  lines `linguist-generated`
- **THEN** the paradigm reports no code size gap for it.

#### Scenario: A byte-bound carrier is not measured

- **WHEN** the repository's format selection declares a tracked JavaScript file with 900 effective
  lines an immutable carrier whose bytes one of its proof gates verifies
- **THEN** the paradigm reports no code size gap for it
- **AND** an invalid carrier declaration leaves the file measured.

#### Scenario: A repository declares a lower ceiling

- **WHEN** `[paradigm.size]` declares `code_effective_lines = 400` and a tracked Go file has 450
  effective lines
- **THEN** the paradigm reports the file and the 400-line ceiling.

#### Scenario: A repository declares a higher ceiling with its reason

- **WHEN** `[paradigm.size]` declares `code_effective_lines = 700` and `[paradigm.size.reasons]`
  states why
- **THEN** a tracked code file with 650 effective lines passes
- **AND** the paradigm report lists the declared value and its reason as a deviation from the
  default.

#### Scenario: An invalid declaration leaves the default in force

- **WHEN** `[paradigm.size]` declares `code_effective_lines = 700` without a reason, declares
  `1200`, declares a value that is not a positive integer or names an unknown key
- **THEN** the paradigm reports the declaration
- **AND** a tracked code file with 650 effective lines is reported against the 500-line ceiling.

#### Scenario: A binding restates a ceiling

- **WHEN** `[paradigm.size]` declares `code_effective_lines = 500`
- **THEN** the paradigm reports a binding that restates a paradigm value.

#### Scenario: A binding declares a retired key

- **WHEN** `[paradigm.size]` declares `python_effective_lines` or `markdown_nonblank_lines`
- **THEN** the paradigm reports the declaration with the repair to rename it `code_effective_lines`
  or `document_nonblank_lines`
- **AND** the default stays in force.

#### Scenario: A binding keeps the retired table

- **WHEN** `.ethos/rules.toml` declares `[quality.code_size]`
- **THEN** the paradigm reports the table with the repair to declare `[paradigm.size]`.
