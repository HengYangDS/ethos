from __future__ import annotations

from ethos.adapters.mutation.resolution.capture import preservation_payloads_match


def test_preservation_payloads_match_requires_exact_v1_or_v2_member_set_and_digests() -> None:
    v1_manifest = {
        "bundle_sha256": "bundle",
        "patch_sha256": "patch",
        "untracked_archive_sha256": "",
    }
    v1_digests = {
        "repository.bundle": "bundle",
        "tracked.patch": "patch",
    }
    v1_names = {"manifest.json", *v1_digests}
    assert preservation_payloads_match(v1_manifest, v1_digests, v1_names)

    v2_manifest = {
        **v1_manifest,
        "package_format_version": "v2",
        "index_patch_sha256": "index",
    }
    v2_digests = {**v1_digests, "index.patch": "index"}
    v2_names = {"manifest.json", *v2_digests}
    assert preservation_payloads_match(v2_manifest, v2_digests, v2_names)

    archive_manifest = {**v2_manifest, "untracked_archive_sha256": "archive"}
    archive_digests = {**v2_digests, "untracked.tar": "archive"}
    archive_names = {"manifest.json", *archive_digests}
    assert preservation_payloads_match(archive_manifest, archive_digests, archive_names)

    assert not preservation_payloads_match(v2_manifest, v2_digests, v2_names - {"index.patch"})
    assert not preservation_payloads_match(v2_manifest, v2_digests, {*v2_names, "extra"})
    assert not preservation_payloads_match(
        archive_manifest,
        {**archive_digests, "untracked.tar": "wrong"},
        archive_names,
    )
