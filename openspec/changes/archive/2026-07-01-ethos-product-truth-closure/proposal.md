# Proposal: Product Truth Closure

## Summary

Harden ETHOS product truth by making target package ontology, migration-host
state, scaffold completeness, command examples, and non-Git initialization
diagnostics explicit and machine-checkable.

## Motivation

ETHOS had target package homes, scaffold generation, and command governance, but
some outputs still implied that physical directories meant migration was
complete. Fresh adopter scaffolds could also fail `ethos status` before Git was
initialized. That weakens UX, DX, and self-governance.

## Scope

- Use a provider-neutral package ontology contract as the machine source for
  target package and migration-host sets.
- Report migration as `in_progress` until active migration hosts are frozen,
  moved, or retired through parity evidence.
- Add `ethos quality package-ontology`.
- Strengthen docs command example checks for unknown `ethos ...` subcommands
  and required proof/governance examples.
- Make `ethos init --apply` and `ethos adopt --apply` apply directly.
- Generate AGENTS, CONTRIBUTING, CHANGELOG, OpenSpec, skills, docs, claims, and
  evidence scaffold files for new adopters.
- Make `ethos status --root <non-git-dir> --json` return stable JSON with a
  clear `git_repository_missing` gap instead of crashing.

## Non-goals

- Do not remove migration-host packages in this change.
- Do not push or publish to a remote.
- Do not touch foreign Work Lanes.
