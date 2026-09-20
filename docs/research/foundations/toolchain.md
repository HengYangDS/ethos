---
subject: ethos:foundations-toolchain
role: research
state: active
relations:
  part_of: ../modern-engineering-foundations.md
  informs: ../../plans/terminal-governance-product-design.md
  constrained_by: ../../governance/product-design-contract.md
---

# Toolchain And Environment Supply

Status: active research; dated observations retain their original evidence limits.

Purpose: Compare native tool selection, package locks and bounded installation.

See also: [Research Overview](../modern-engineering-foundations.md),
[Product Design Contract](../../governance/product-design-contract.md), and
[Terminal Plan](../../plans/terminal-governance-product-design.md).

## Toolchain And Environment Ownership

The release API reported mise `v2026.9.5`, Pixi `v0.80.0`, CUE `v0.17.1`, Pants
`release_2.33.1`, Dagger `v0.21.9` and Allure `v3.17.0` as their latest
non-prerelease tags at collection. These are observations, not permanent pins or
an authorization to auto-upgrade. A selected dependency needs supported-platform,
license, integrity, locked-supply and failure-path verification.

| Candidate | Verified capability | Replacement test |
| --- | --- | --- |
| [mise][mise] | Release documentation separates requested versions from resolved tool artifacts and supported checksums; [security controls][mise-security] distinguish config trust from artifact verification | Strong candidate for developer/CI tool bootstrap. Replace duplicated binary discovery/download/version checks only where its backend guarantees suffice. Keep ecosystem locks for package dependencies; mise's lock does not lock every external dependency. |
| [Pixi][pixi] | Cross-platform, multi-language environment management; [environment contract][pixi-environment] binds synchronization to its lock | Compare an integrated native tool environment against the present Python/Node supply. Require offline installation, exact platform closure and coexistence with a separately distributed ETHOS package. A Pixi environment is not ETHOS runtime activation. |
| [uv][uv] | Python project, interpreter and package management with a shared cache | Treat as a strong baseline for Python, not a mandated permanent choice. Remove local dependency-resolution substitutes while retaining ETHOS acceptance, immutable inventory and selector responsibilities. |
| [Nix][nix] | Declarative build/package foundation | Reference candidate for reproducible supply and content-addressed builds. Native Windows delivery and user adoption cost need independent evidence; no blanket cross-platform claim. |

mise's [artifact cache][mise-cache] is explicitly experimental in the inspected
release; ordinary freshness checks use modification times. Neither is an
acceptable substitute for complete proof-input identity. Do not put proof trust
on an experimental convenience cache merely because the tool itself is stable.

Choose either a split ownership model, such as tool bootstrap plus native Python
and Node locks, or an integrated environment model. Independent package manifests
remain necessary for distributed packages; duplicated editable resolutions for
the same runtime do not. The experiment must name precisely which installers,
launchers, discovery rules and supply copies disappear.

### Native mise Replacement Evidence

September 20, 2026, Asia/Shanghai: the installed Homebrew mise 2026.9.11 generated
CUE 0.17.1 and actionlint 1.7.12 locks for macOS arm64/x64, Linux arm64/x64 and
Windows x64. Two native lock refreshes preserved every lock byte. They still
re-downloaded actionlint artifacts for provenance verification and took about
9 seconds each; lock refresh belongs to supply updates, not every proof.
A warm locked-install preview took 0.016 seconds and installed nothing.
A later empty-cache isolated install took 7.359 seconds; its warm repeat took
0.017 seconds, installed nothing, and preserved the lock bytes. Both tools ran
successfully from that supply and the owned temporary installation was removed.
`build/evidence/quality/commit-integrity/mise-cold-warm.json` contains the result.

The bounded implementation uses the native resolver with exact supplied config
and lock bytes in an owned temporary directory. Safe mode disables project hooks;
operator tool storage remains available, while ambient configuration is excluded.
Missing locks and mismatched selections fail instead of finding an ambient tool.
CUE and workflow-gate regressions execute native binaries. The former actionlint
downloader is replaced by a thin invocation of the same locked supply owner.

A deliberate altered archive checksum still allowed `mise which` to return an
already installed binary. This is not archive verification or an installed-byte
integrity proof. Keep trusted supply selection and execution identity independent;
do not replace stronger installed-runtime verification with a version string.
The evidence in `build/evidence/quality/commit-integrity/mise-lock-repro.json`
and the `mise-*-red.log` / `mise-*-green.log` files is local candidate evidence,
not hosted qualification, complete supply migration or product installation.

Native retained-download execution is now qualified on the local candidate for
SCC, gitleaks and Syft. `mise-native-real-activation.json` records real cold
provisioning followed by 0.052/0.166/0.191-second verified warm reuse, unchanged
executable identity and complete isolated-root cleanup. The existing materializer
delegates download/install to native mise in temporary storage and keeps only
archive/member verification, cache publication and execution identity checks.
Its custom download retry/transport and subprocess supervisor were replaced.
The 292-case consumer run is focused evidence, not full or hosted acceptance.

The fixed [native install implementation][mise-native-install] takes a
tool/version lock but removes an existing target before forced replacement.
Consequently `mise install --force` on the active executable is not a substitute
for the existing failure-preserves-old-content obligation. Staging native
provisioning outside the active target satisfies that distinction without
implementing a second installer. Native safe mode excludes project hooks and
settings, not the operating system; required safety and storage controls are
explicit caller environment, with ambient mise configuration excluded.

The native generated bootstrap was replayed in an isolated environment without
mise on PATH. It prepared mise, CUE and actionlint in 15.24 seconds, reused them
in 2.98 seconds, and removed its entire temporary root. An initial migration
warning exposed unsafe version observation; safe mode removed the cause and a
negative regression rejects remaining version diagnostics. The selected wrapper
is reproduced with native generation plus one equivalent quoted-tilde pattern
normalization and shfmt; its drift is rejected. These observations do not prove
Linux/Windows bootstrap, hosted CI or installed ETHOS product completion.

## Sources

Links identify inspected documents, not blanket endorsements. Source-level and
README observations above have different strength; repository popularity and
marketing claims were not used as evidence of comparative performance.

[mise]: https://github.com/jdx/mise/blob/016fcd16a991c85e099d4f0b571bc44978a9eb94/docs/dev-tools/mise-lock.md
[mise-security]: https://github.com/jdx/mise/blob/016fcd16a991c85e099d4f0b571bc44978a9eb94/docs/security.md
[mise-cache]: https://github.com/jdx/mise/blob/016fcd16a991c85e099d4f0b571bc44978a9eb94/docs/tasks/caching.md
[pixi]: https://github.com/prefix-dev/pixi/blob/56ae6f39b887a954242002deeda5372f80b34a87/README.md
[uv]: https://github.com/astral-sh/uv/blob/8e70deb71b410d4bcf80fabdd88e8aa43a2e5878/README.md
[nix]: https://github.com/NixOS/nix/blob/203f85b2e851fc52e253e8e33eff5fb92936736a/README.md
[pixi-environment]: https://github.com/prefix-dev/pixi/blob/56ae6f39b887a954242002deeda5372f80b34a87/docs/workspace/environment.md
[mise-native-install]: https://github.com/jdx/mise/blob/v2026.9.11/src/backend/mod.rs
