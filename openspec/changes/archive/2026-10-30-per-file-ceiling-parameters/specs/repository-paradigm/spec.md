## MODIFIED Requirements

### Requirement: Python files stay within the common size ceiling

Every tracked Python file SHALL have at most as many effective lines, counted without blank
lines, comments and docstrings, as its repository's Python ceiling. The paradigm contract SHALL
hold both per-file ceilings' default of 500 and bound of 1000. A repository binding MAY declare
its own whole-tree value in `.ethos/rules.toml` `[paradigm.size]`; an invalid declaration SHALL
be reported and leave the default in force. No binding SHALL set a ceiling for one file, path or
class of files.

#### Scenario: A Python file outgrows the ceiling

- **WHEN** a governed repository that declares no Python ceiling tracks a Python file with 501 effective lines
- **THEN** the paradigm reports the file and the 500-line ceiling.

#### Scenario: A repository declares a lower ceiling

- **WHEN** `[paradigm.size]` declares `python_effective_lines = 400` and a tracked Python file has 450 effective lines
- **THEN** the paradigm reports the file and the 400-line ceiling.

#### Scenario: A repository declares a higher ceiling with its reason

- **WHEN** `[paradigm.size]` declares `python_effective_lines = 700` and `[paradigm.size.reasons]` states why
- **THEN** a tracked Python file with 650 effective lines passes
- **AND** the paradigm report lists the declared value and its reason as a deviation from the default.

#### Scenario: An invalid declaration leaves the default in force

- **WHEN** `[paradigm.size]` declares `python_effective_lines = 700` without a reason, declares
  `1200`, declares a value that is not a positive integer or names an unknown key
- **THEN** the paradigm reports the declaration
- **AND** a tracked Python file with 650 effective lines is reported against the 500-line ceiling.

#### Scenario: A binding restates a ceiling

- **WHEN** `[paradigm.size]` declares `python_effective_lines = 500`
- **THEN** the paradigm reports a binding that restates a paradigm value.

#### Scenario: A binding keeps the retired table

- **WHEN** `.ethos/rules.toml` declares `[quality.code_size]`
- **THEN** the paradigm reports the table with the repair to declare `[paradigm.size]`.
