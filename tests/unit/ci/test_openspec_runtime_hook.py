import pytest

import tools.ci.openspec_runtime_hook as subject


@pytest.mark.parametrize("failure", [False, True])
def test_build_hook_reclaims_owned_supply(tmp_path, monkeypatch, failure) -> None:
    hook = subject.OpenSpecRuntimeHook(  # type: ignore[invalid-argument-type]
        str(tmp_path), {}, object(), object(), "build", "sdist"
    )
    monkeypatch.setattr(subject.tempfile, "tempdir", str(tmp_path))
    identity = (b'{"schema_version":1}\n', "0.2.0a1.dev0+gaaaaaaaaaaaa.tbbbbbbbbbbbb")
    monkeypatch.setattr(
        subject,
        "_build_identity_payload",
        (lambda _: pytest.fail("identity failed")) if failure else lambda _: identity,
    )
    data = {"force_include": {}}
    if failure:
        with pytest.raises(pytest.fail.Exception):
            hook.initialize("standard", data)
    else:
        hook.initialize("standard", data)
        hook.finalize("standard", data, "artifact.whl")
    assert not list(tmp_path.glob("ethos-openspec-supply-*"))
