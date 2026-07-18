# Design

The change follows the existing scorecard shape:

- `hard_quality_floor_report(repo)` remains the single product report read model
  for hard quality floor aggregation.
- Coverage uses `coverage_quality_report(repo)` from the coverage policy owner.
- Types use `ty_gate_report(repo)` from the ty adapter policy owner.
- Docstrings use `docstring_coverage_report(repo)` from the docstring policy
  owner.
- `scorecard_next_actions` routes each required gap to the narrowest existing
  `ethos quality ...` command.

No new command, truth store, profile role, or provider ontology is introduced.
The report only reveals hard gate verdicts that already exist elsewhere.
