## Context

ETHOS is the governing product. Adopter repositories such as reference adopter provide
profiles, rules, skills, and domain contracts, but those semantics must not be
hardcoded into product core.

## Decisions

- Treat `ethos-repository` as the product family for init, adopt, scaffold,
  profile, and fleet inspection.
- Treat `ethos-distribution` as the family for npm and future package-manager
  launchers. Launcher packages forward to the Python command plane and do not
  own governance semantics.
- Treat `.agents/skills` as the default repo-local playbook projection. It is
  configurable in adopter repositories, but it is not an assistant truth store.
- Keep official OpenSpec records under `openspec/` and validate them with the
  official OpenSpec CLI. Split canonical specs by product family so a passing
  OpenSpec check also covers MECE topology.
- Make self-audit fail on missing claims, missing playbooks, missing spec
  families, malformed evolution ledgers, and retired public command roots in
  current docs.
- Make capability parity closure depend on tracked shadow evidence rather than
  static ledger disposition. A verified capability must be named in
  `docs/evidence/parity/<adopter>-shadow.json`, and the shadow report must have
  no required gaps.
- Adopt mature standards as adapters with explicit contracts and exit
  strategies before introducing service-mode or hosted integrations.

## Risks / Trade-offs

- Renaming `ethos-adopt` to `ethos-repository` is a breaking internal package
  change. This is acceptable because the public command remains `ethos adopt`
  and no compatibility shell is retained.
- A complete scaffold writes more files. Apply mode preserves existing non-empty
  files to avoid damaging adopter repositories.
- Official OpenSpec validation proves record health, not product truth. ETHOS
  promotes the record into tests, docs, schemas, and command behavior.
