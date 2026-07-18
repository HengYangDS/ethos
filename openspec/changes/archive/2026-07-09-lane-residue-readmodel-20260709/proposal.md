# Work Lane residue read-model hardening

## Why

`landed_dirty` lanes are visible today, but the read model does not name the residue state or the preservation path. Humans and agents can therefore mistake a landed dirty lane for ordinary retire-ready residue.

## What

- Add explicit residue state and next action to foreign Work Lane status items.
- Keep foreign lanes observe-only; do not authorize write, land, or retire from visibility.
- Document the distinction between clean landed retirement and dirty landed preservation.
