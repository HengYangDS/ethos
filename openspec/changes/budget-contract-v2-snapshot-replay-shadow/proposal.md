# Budget Contract v2 Git Snapshot Replay And Shadow

## Why

Budget Contract v2 now has typed carriers, versioned native measurement, and an
accepted static-hybrid resource boundary, but the migration still lacks an
immutable Git-blob replay and a truthful shadow comparison. The declared v1
baseline must remain `105342`. Versioned observer profile
`v1-continuation-20260719` replays that historical tree as `105060`, so the
`-282` drift is a governed observation rather than a reason to rewrite the
declaration. The later live Task 4-start taxonomy intentionally omits Jinja and
therefore yields a separate `104389` observation that must remain unresolved,
not overwrite the historical correction.

The replay boundary must not create temporary checkouts or worktrees. It must
bind the selected commit, tree, inventory, blob identities, measurement
contracts, and fail-closed gaps before a comparison can be reviewed.

## What Changes

- Add public source/bytes measurement boundaries so immutable blobs reuse the
  canonical ELOC and Budget Contract v2 measurement logic without private
  imports or duplicated parsers.
- Add a strict Git snapshot adapter that peels a treeish to full commit/tree
  identities, parses NUL-framed `git ls-tree` output, and reads selected blobs
  through one validated `git cat-file --batch` exchange.
- Replay the immutable baseline commit
  `2dab77f169eceb2d45f917358c2a7487e7ac8db6` and tree
  `075da5ad45be962e9f5e775b3f050cab4023ea0d`, binding subject snapshot and
  observer taxonomy independently.
- Bind historical observer profile `v1-continuation-20260719` at commit
  `604934c7afe244caf5b671423f108823a7753a98`, taxonomy blob
  `51a3931b43aa9030e166309289d6d85a80831526`, and taxonomy content SHA-256
  `b5dfc532586b0e1f3c3f614ce34e70cd9e817b84adfeabfbda266adf19d07a3d`;
  it yields 933 governed files and inventory SHA-256
  `f8e85ace7648b60592fbe6e678f78169afa98c6289b0e8bb7d7fbc3961fa1c8d`.
- Bind live observer profile `v1-live-at-task4-start` at commit
  `fe94c0268d060742e808770d4d65d554709af0dd`, taxonomy blob
  `280f4ff640b0d6088c6fc819bebca2c6a7de5fea`, and taxonomy content SHA-256
  `3180f9739fc254c29fa6ca6924818a2c3eb5d1ccedd0fe1916e88a05e1b41983`;
  it yields 888 governed files, inventory digest
  `d48fca7255274216d029c600b98972f00bd367b91979441b4d6512a857fb7a5c`,
  global `104389`, and no Jinja coordinate.
- Preserve declared v1 total `105342`, report replay total `105060`, and expose
  only JavaScript `89 -> 90`, YAML `1082 -> 800`, and diagram `24 -> 23` as
  changed categories.
- Add versioned replay history configuration, a repository-owned CLI and shell
  wrapper, ignored raw replay artifacts, and reviewed Claim/Chronicle summaries.
- Preserve current v1 top-level `ok`, `state`, and `required_gaps` fields while
  adding a `v2_shadow` observer that never converts unresolved disagreement into
  a clean state.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `contracts`: subject=budget-contract-v2-snapshot-replay-shadow;
  reuse=extend; change=modify;
  facet:lifecycle=authoring,validation,migration;
  facet:surface=contract,adapter,tool,evidence;
  facet:authority=source,test,config,openspec,claim,evidence.
- `quality`: subject=budget-contract-v2-snapshot-replay-shadow;
  reuse=extend; change=modify;
  facet:lifecycle=authoring,validation,migration;
  facet:surface=policy,report,tool,evidence;
  facet:authority=source,test,config,openspec,claim,evidence.

## Impact

This Change adds immutable snapshot loading, replay/shadow reporting, focused
contract and adversarial tests, history configuration, a tool declaration, and
reviewed evidence. Raw per-file observations remain ignored under
`build/evidence/quality/source-budget-v2/replay/`.

## Out Of Scope

- Rewriting the v1 declaration or changing v1 allowance, debt, terminal targets,
  repository-wide LOC enforcement, or per-file ELOC.
- Resolving the accepted C1 YAML adapter gap or treating the checkpoint
  `3468ce78e2b636b9c0516904aa73cde2eb30fa62` as clean.
- Task 5+ vector policy, Debt v2, changed-scope/source-admission gates, dual
  control, cutover, global v1 LOC retirement, terminal settlement, archive,
  candidate/accepted promotion, remote publication, or Lane retirement.
