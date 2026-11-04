# Tasks

## 1. Decision citation

- [x] 1.1 Report each decision record that names the active Change in inline code but that the
      Change never cites. Done when a test shows that archive readiness blocks a Change that a
      record names with `openspec_decision_uncited:<change>:<identity>`, passes once an artifact
      cites the record by identity or by file name, ignores a record that names the Change only in
      prose, and failed before the change. The uncited case failed before it; the four cases and
      1,309 OpenSpec, repository, architecture and proof admission tests pass.
- [x] 1.2 State the rule in the Docs Registry guide. Done when the decision record contract names
      it.
- [x] 1.3 Record the change in the changelog. Done when the unreleased Added section names it.

## 2. Specification

- [x] 2.1 Write the `repository-governance` delta. Done when strict validation and the cumulative
      archive simulation pass. The Change validates strictly, and the cumulative archive simulation
      of the lane's eleven Changes keeps all 12 specs strictly valid.
