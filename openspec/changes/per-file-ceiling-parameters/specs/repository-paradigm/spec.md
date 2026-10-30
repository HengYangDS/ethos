## MODIFIED Requirements

### Requirement: Python files stay within the common size ceiling

Every tracked Python file SHALL have at most as many effective lines, counted without blank lines, comments and docstrings, as its repository's effective Python ceiling. The paradigm contract SHALL hold the default of each per-file ceiling, 500 for Python files and 500 for the Markdown documentation ceiling, and one bound of 1000 for both. A repository binding MAY declare its own value for either ceiling in `.ethos/rules.toml` under `[paradigm.size]`, and that value applies to every file the ceiling measures. A lower value SHALL apply. A higher value SHALL apply only when it is within the bound and `[paradigm.size.reasons]` states a reason for it, and the paradigm SHALL report it as a deviation from the default. A value equal to the default, a higher value without a reason, a value above the bound, a value that is not a positive integer and an unknown key SHALL each be reported, and the default SHALL apply. No binding SHALL set a ceiling for one file, a path or a class of files.

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

#### Scenario: A higher ceiling lacks its reason or exceeds the bound

- **WHEN** `[paradigm.size]` declares `python_effective_lines = 700` without a reason, or declares `1200`
- **THEN** the paradigm reports the declaration
- **AND** a tracked Python file with 650 effective lines is reported against the 500-line ceiling.

#### Scenario: A binding restates a ceiling

- **WHEN** `[paradigm.size]` declares `python_effective_lines = 500`
- **THEN** the paradigm reports a binding that restates a paradigm value.

#### Scenario: A binding keeps the retired table

- **WHEN** `.ethos/rules.toml` declares `[quality.code_size]`
- **THEN** the paradigm reports the table with the repair to declare `[paradigm.size]`.
