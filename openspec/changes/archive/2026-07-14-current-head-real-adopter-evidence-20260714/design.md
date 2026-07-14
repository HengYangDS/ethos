## Context

An existing ETHOS adopter retains its own profile, skills, OpenSpec carriers,
repository-native proof gates, and `pixi run ethos` command. The observation
compares that native surface against the product candidate runtime without
mutating the source checkout.

## Decisions

### Preserve adopter-owned governance

Generic overlay conflicts must remain conflicts. An authorized apply that
refuses before writing is evidence of preservation, not a reason to replace
adopter-owned surfaces.

### Bind execution to the candidate source tree

The external command runtime resolves ETHOS modules from the named candidate
source tree. The Chronicle binds the product Git revision and tree alongside
the isolated adopter revision and tree, while retaining only a digest of the
host-local raw results.

### Documentation routes, not duplicates

`docs/evidence/` and `docs/history/` link to this bounded record. Claims and
Chronicles remain the evidence authority; documentation copies neither raw
payload nor local identity.

## Risks / rollback

Matching command results do not establish semantic compatibility, hosted
execution, authority, or independent review. Revert this carrier, claim,
Chronicle, and routing links to remove the observation. The adopter and all
remote state remain untouched.
