# Root Host Residue Gate

## Problem

The accepted root can appear Git-clean while a globally ignored host-local file
such as `.DS_Store` remains in the repository root. That is a small drift signal:
local workstation residue is hidden from Git status and can normalize pollution
of the repository boundary.

## Change

Harden the repository hygiene owner script so it reads a separated policy file
under `.config/checks/repository-hygiene/` and fails closed when configured
root-only host-local residue is present. The gate reports the residue; it does
not delete, stash, or promote it.

## Capabilities

- `quality`: subject=root-host-residue-hygiene; reuse=extend; change=modify;
  facet:lifecycle=quality; facet:surface=ci,script,config,test,openspec;
  facet:authority=source,test,system,openspec,evidence

## Out Of Scope

- No cleanup command, stash carrier, new truth store, or provider-specific logic.
- No scan of ignored build/runtime/evidence directories.
- No change to Work Lane ownership or candidate/accepted closeout semantics.
