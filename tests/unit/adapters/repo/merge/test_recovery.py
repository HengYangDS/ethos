"""Destructive merge preimages preserve exact file kinds and refuse unsafe bytes."""

import json
from pathlib import Path

import pytest

from ethos.adapters.repo.merge.observation import observe_merge
from ethos.adapters.repo.merge.recovery import preserve_merge
from tests.support.openspec_lifecycle import native_merge_fixture


@pytest.mark.parametrize("case", ["absent", "symlink", "directory", "stale"])
def test_recovery_inventory_preserves_kinds_and_rejects_unsafe_or_stale_bytes(tmp_path, case):
    """Destructive preimages distinguish absence, link payload and unsupported file kinds."""
    work = native_merge_fixture(tmp_path)
    observed = observe_merge(work)
    path = work / "README.md"
    if case == "stale":
        path.write_text("changed after observation\n")
    else:
        path.unlink()
        if case == "symlink":
            path.symlink_to("unread-target")
        elif case == "directory":
            path.mkdir()
        observed = observe_merge(work)
    if case in {"directory", "stale"}:
        with pytest.raises(ValueError, match=r"merge_recovery_content_unsafe|merge_state_stale"):
            preserve_merge(work, observed)
    else:
        artifact = preserve_merge(work, observed)
        artifact_path = artifact["path"]
        assert isinstance(artifact_path, str)
        data = json.loads(Path(artifact_path).read_text())
        assert data["files"]["README.md"]["kind"] == ("absent" if case == "absent" else "symlink")
        assert preserve_merge(work, observed) == artifact
