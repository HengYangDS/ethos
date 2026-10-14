"""Verify native producer ownership without publication prerequisites."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.repository.policy.projections import observe_projections
from ethos.repository.policy.projections import projection_effect_gaps
from ethos.repository.policy.projections import projection_relations
from ethos.repository.policy.projections import render_architecture

if TYPE_CHECKING:
    from pathlib import Path


_CI = ".config/checks/ci-projection/policy.toml"
_CI_SCHEMA = 'schema = "ethos-ci-template-consistency-v1"\n'


@pytest.mark.parametrize(
    ("entries", "reason"),
    [
        ('projection = ["copy"]\n', "projection_kind_unknown"),
        (
            '[[projection]]\nkind = "shell"\ntemplate = "a.yml"\nprojection = "b.yml"\n',
            "kind_unknown",
        ),
        ('[[projection]]\ntemplate = "a.yml"\nprojection = "a.yml"\n', "projection_owner_conflict"),
        (
            (
                '[[projection]]\ntemplate = "a.yml"\nprojection = "b.yml"\n'
                '[[projection]]\ntemplate = "c.yml"\nprojection = "b.yml"\n'
            ),
            "projection_owner_conflict",
        ),
        (
            f'[[projection]]\ntemplate = "a.yml"\nprojection = "{_CI}"\n',
            "projection_owner_conflict",
        ),
        (
            '[[projection]]\nkind = "cue"\nprovider = "ci"\nprojection = "b.yml"\n',
            "compiler_invalid",
        ),
        ('[[projection]]\ntemplate = 1\nprojection = "b.yml"\n', "projection_path_invalid"),
        (
            "[[projection]]\ntemplate = 'a\\b.yml'\nprojection = 'b.yml'\n",
            "projection_path_invalid",
        ),
        (
            '[[projection]]\ntemplate = "../source.yml"\nprojection = "b.yml"\n',
            "projection_path_invalid",
        ),
        (
            '[[projection]]\ntemplate = "/source.yml"\nprojection = "b.yml"\n',
            "projection_path_invalid",
        ),
        ('[[projection]]\ntemplate = "."\nprojection = "b.yml"\n', "projection_path_invalid"),
    ],
    ids=[
        "entry",
        "kind",
        "self",
        "shared-output",
        "declaration-output",
        "compiler",
        "type",
        "slash",
        "parent",
        "absolute",
        "directory",
    ],
)
def test_projection_declarations_keep_one_exact_native_owner(entries: str, reason: str) -> None:
    """Each output has one declared producer with an exact native kind and local path."""
    with pytest.raises(ValueError, match=reason):
        projection_relations({_CI: _CI_SCHEMA + entries})


def test_compiled_projection_is_never_rendered_or_checked_without_its_compiler() -> None:
    """A CUE relation binds its compiler inputs and needs native compiled bytes to compare."""
    declaration = _CI_SCHEMA + (
        '[compiler]\nsource = "ci.cue"\ninputs = {schema = "schema.cue"}\n'
        'supply = {config = "cue.mod/module.cue", lock = "cue.lock"}\n'
        '[[projection]]\nkind = "cue"\nprovider = "ci"\nprojection = "ci.yml"\n'
        '[[projection]]\ntemplate = "copy.yml"\nprojection = "copied.yml"\n'
    )
    cue, copy = projection_relations({_CI: declaration})
    assert cue.materials == (
        _CI,
        "ci.cue",
        "schema.cue",
        "cue.mod/module.cue",
        "cue.lock",
        "ci.yml",
    )
    with pytest.raises(ValueError, match=r"projection_requires_native_compiler:ci\.yml"):
        cue.render("")
    files = dict.fromkeys((*cue.materials, *copy.materials), "")
    assert projection_effect_gaps((cue, copy), (cue, copy), files, {"copy.yml": ""}) == []
    with pytest.raises(ValueError, match=r"compiled_projection_unavailable:ci\.yml"):
        projection_effect_gaps((cue, copy), (cue, copy), files, {"ci.cue": ""})


def test_architecture_projection_renders_only_the_declared_subset() -> None:
    """Comments and blank lines vanish; nodes keep descriptions and relations keep labels."""
    text = (
        '# owner\n\nsystem ethos "ETHOS" "Governance"\n'
        'container cli "CLI"\nrel cli ethos "invokes"\n'
    )
    assert render_architecture("architecture.c4", text) == (
        "%% Generated from architecture.c4. Do not edit by hand.\n"
        "flowchart LR\n"
        '  ethos["ETHOS Governance"]\n'
        '  cli["CLI"]\n'
        '  cli -->|"invokes"| ethos\n'
    )


def test_projection_declaration_must_stay_inside_the_repository(tmp_path: Path) -> None:
    """A linked declaration outside the repository is not a local producer owner."""
    outside = tmp_path / "outside.toml"
    outside.write_text(_CI_SCHEMA)
    link = tmp_path / "repo" / _CI
    link.parent.mkdir(parents=True)
    link.symlink_to(outside)
    with pytest.raises(ValueError, match="projection_declaration_outside_root"):
        observe_projections(tmp_path / "repo")
