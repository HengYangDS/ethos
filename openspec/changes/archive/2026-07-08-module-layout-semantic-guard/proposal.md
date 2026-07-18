---
subject: ethos:module-layout-semantic-guard
reuse: extend
change: modify
facet:lifecycle: validation
facet:surface: quality
facet:authority: rule,test,source
---

# Module Layout Semantic Guard

## Why

The module-layout gate already tracks suffix-flat modules, import-only facades,
private alias residue, same-directory flat growth, and ratchet baselines. Two
normal write paths were still too easy to misread:

- creating a brand-new directory with many direct modules in one change, which
  avoids the existing-dir flat-growth guard while still producing a flat bucket;
- hiding compatibility exports behind module-level `__getattr__`, which avoids
  the import-only facade detector while preserving an old surface.

Both patterns violate the semantic-subpackage rule and make the repository look
more modular than it is.

## What Changes

- Extend module-layout growth checks to block brand-new directories that add more
  than the configured direct-module burst limit.
- Extend facade checks to block module-level `__getattr__` dynamic export shells.
- Update rule text and focused tests so the guard is understandable and
  regression-proof.

## Capabilities

- `quality`: subject=module-layout-semantic-guard; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=quality,rule,test,openspec; facet:authority=source,test,rule,openspec,evidence

## Out Of Scope

- No broad package or CLI decomposition in this lane.
- No compatibility import shells are added.
- Existing ratcheted layout debt is not re-baselined upward.
