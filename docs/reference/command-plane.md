---
subject: ethos:command-plane
role: reference
state: canonical
relations:
  canonical_for: public commands
---

# Command Plane

Public daily commands:

```bash
ethos status
ethos plan
ethos prove
ethos land
ethos publish
```

The npm launcher exposes the same root command:

```bash
npm run ethos -- --version
```

Advanced commands remain under `ethos ...`. Retired root commands are not
compatibility surfaces.

Quality and governance:

```bash
ethos quality command-registry
ethos quality command-surface
ethos quality command-examples
ethos quality claims
ethos quality docs-registry
ethos quality gates
ethos quality provenance
ethos quality schemas
ethos quality commits
ethos quality release
ethos quality standards
ethos self audit
ethos self audit --mode shape
ethos self audit --mode deep
ethos self hypothesize
ethos self prove --mode shape
ethos self prove --mode deep
ethos campaign hypotheses
ethos intake status
ethos parity ledger
ethos parity gaps --adopter alphasim-dmgr
ethos parity shadow --target <repo>
ethos report
```

Agent projections:

```bash
ethos assistants doctor
ethos assistants check-projections
ethos assistants mcp-manifest
ethos assistants mcp-server
```

Playbook routing:

```bash
ethos playbooks check
ethos playbooks route
ethos playbooks route --changed
```

Work Lane admission:

```bash
ethos lane status
ethos lane candidate --path <candidate-worktree-path> --apply --expect-head <git-head>
ethos lane start <name> --path <worktree-path> --owner <owner> --apply
ethos lane prewrite <path> --editor-root <worktree-path> --require-editor-root
```

Mutation readiness is explicit:

```bash
ethos land --apply --authorize --expect-head <git-head>
ethos publish --apply --authorize --expect-head <git-head>
```

Those commands still report readiness in the current implementation; remote
publication remains an adapter responsibility. `land --apply` from an admitted
Work Lane advances local `candidate/dev`; it does not advance `dev`.

Self-governance modes are explicit. `shape` is the daily fast path for product
shape, schemas, claims, command vocabulary, and OpenSpec layout. `deep` includes
official OpenSpec CLI validation and is required for release or archive proof.
