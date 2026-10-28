---
subject: ethos:guide:release-and-publication
role: how-to
state: active
relations:
  canonical_for: cutting an ETHOS release and activating a second Forge
---

# Release And Publication

Status: active.

Purpose: cut an ETHOS product release from accepted source, and add a second Forge to a repository's publication topology.

See also: [ETHOS source distribution specification](../../openspec/specs/distribution/spec.md "source-only") for versions, stages and release entries; [ETHOS source repository-governance specification](../../openspec/specs/repository-governance/spec.md "source-only") for publication topology and peers; [Release Rules](../../rules/release.md); and [Command Plane](../reference/command-plane.md).

## Cut A Release

1. **Open a release Change** in its own Work Lane. Move the product version in `VERSION`, `distributions/npm/package.json` and its `package-lock.json` entry. Then curate the release entry in `CHANGELOG.md` from the Unreleased notes and every user-visible change since the previous tag. The distribution specification owns the version, stage and entry rules.
2. **Archive, prove and land.** Archive the Change with `ethos lane archive-change`, then prove the archived head once with `ethos prove --execute --full --expect-head <HEAD> --json`. If that proof fails, `ethos lane archive-change --compensate` returns the lane to its pre-archive head. Then land, close out and bootstrap the accepted root.
3. **Publish the branches.** Publish `dev`, then `main`, to each declared peer with `ethos publish --probe-remote --ref <ref> --peer <id> --expect-head <HEAD> --json`, followed by the receipt action it returns.
4. **Tag.** When the landed head's hosted runs pass on every supported platform (the practised order; the distribution specification states what each stage requires), create the signed annotated tag: preview `ethos land --release --expect-head <accepted-head> --release-head <main> --tag v<version> --json`, then apply it with `--apply --authorize`. Publish the tag with the same publish probe and receipt.
5. **Build the release.** Dispatch the hosted `ETHOS CI` workflow on `main` with its `release_tag` and `release_head` inputs. Verify the published assets. Name in the release entry each journey that the target does not declare, or whose environment was unavailable.

## Activate A Second Forge

1. **Declare the peer** under `[[publication.peers]]` in `.ethos/release.toml`.
2. **Add its projection.** Add its `[[projection]]` and `[[forge_surface]]` entries in `.config/checks/ci-projection/policy.toml`.
3. **Write the generated files.** Preview and apply them with `ethos lane project`.
4. **Check them.** Run `uv run --frozen --offline python -m nox -s ci_templates`.
5. **Prove the head.** Run `ethos prove --execute --full --expect-head <HEAD> --json`.
6. **Optional emulator evidence.** Record it with `uv run --frozen --offline python tools/ci/ci_templates.py emulator-evidence <provider>`. It is local evidence only.
7. **Observe the hosted run.** Record the hosted run with the `hosted_observation` Nox session in execute mode (`ETHOS_HOSTED_OBSERVATION_EXECUTE=1`) before claiming hosted success. Each Forge's hosted observation stays a separate proof plane.
