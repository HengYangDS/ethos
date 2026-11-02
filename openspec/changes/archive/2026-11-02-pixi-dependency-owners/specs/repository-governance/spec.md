## ADDED Requirements

### Requirement: A Pixi conda dependency owns the executable it names

Each conda package that the repository's Pixi manifest declares, in any conda dependency table of
`pixi.toml` or, without one, of `[tool.pixi]` in `pyproject.toml`, SHALL own the executable of its
package name on every platform, installed or not. Its other executables, PyPI dependencies and
constraints SHALL own nothing.

#### Scenario: A declared package is documented

- **GIVEN** `pixi.toml` declares `pip = "*"` in `[feature.host.dependencies]`
- **WHEN** a patch touches a guide whose `bash` fence runs `pip install -e packages/core`
- **THEN** prewrite admits `pip`
- **AND** `pip3` stays refused
