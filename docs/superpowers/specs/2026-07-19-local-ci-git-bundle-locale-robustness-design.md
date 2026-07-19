# Local CI Git Bundle Locale Robustness Design

## Problem

The full local CI fallback fails on a Chinese-locale workstation because one
cross-host handoff test asserts the English phrase `complete history` from
`git bundle verify`. Git returns an equivalent localized message, so the bundle
is valid while the test fails.

## Options

1. Run only this external Git assertion with `LC_ALL=C` and `LANG=C`.
2. Replace the message assertion with exit-code and ref checks, weakening the
   explicit complete-history observation.
3. Force every test Git subprocess into the C locale, broadening the change to
   unrelated contracts.

## Decision

Use option 1. The test will invoke `git bundle verify` directly with a copied
environment whose message locale is fixed to `C`. Product code, bundle format,
handoff behavior, shared Git helpers, and all other tests remain unchanged.

## Data Flow

The handoff exporter writes the bundle. The test invokes Git against that exact
bundle, requires a zero exit status, captures the deterministic C-locale output,
and retains the `complete history` assertion.

## Failure Handling

Git command failure remains a test error through `check=True`. A bundle that is
not complete continues to fail the semantic phrase assertion. Host locale no
longer affects the observed text.

## Verification

- Preserve the observed RED failure under `LC_ALL=zh_CN.UTF-8`.
- Run the focused test under the workstation locale after the change.
- Run the complete local CI fallback on a stable HEAD.
- Refresh parity, execute HEAD-bound proof, archive, land, close accepted root,
  and retire the owned Work Lane.

## Boundaries

No remote push, tag, hosted-CI claim, product runtime change, shared helper
change, or foreign Work Lane mutation is included.
