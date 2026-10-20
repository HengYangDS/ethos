"""Repository-authored names and the multi-Forge pipeline model."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.repository.paradigm.report import paradigm_path_gaps
from tests.support.paradigm import CONFORMING
from tests.support.paradigm import paradigm_report

if TYPE_CHECKING:
    from pathlib import Path

_GITLAB = ".gitlab-ci.yml"
_GITHUB = ".github/workflows/verify.yml"


@pytest.mark.parametrize(
    ("path", "carrier", "kebab"),
    [
        ("rules/module_layout.md", "rules/module_layout.md", "rules/module-layout.md"),
        ("content/Design_Notes/intro.md", "content/Design_Notes", "content/design-notes"),
        ("styles/StockPhrases.yml", "styles/StockPhrases.yml", "styles/stock-phrases.yml"),
        ("media/captions.zh_CN.srt", "media/captions.zh_CN.srt", "media/captions.zh-cn.srt"),
        ("Product_Area/intro.md", "Product_Area", "product-area"),
    ],
    ids=["snake-file", "directory", "camel-file", "suffix", "product-root"],
)
def test_an_authored_name_outside_kebab_case_names_its_kebab_form(
    tmp_path: Path, path: str, carrier: str, kebab: str
) -> None:
    """The gap names the kebab-case form, and marking the path received for a third-party file."""
    report = paradigm_report(tmp_path, {**CONFORMING, path: ""})
    assert report["required_gaps"] == [f"repository_paradigm_authored_name:{carrier}"], report
    assert report["next_action"] == (
        f"rename {carrier} to {kebab} and update its references, or mark it linguist-vendored "
        "or linguist-generated in .gitattributes if it is third-party or generated"
    )


@pytest.mark.parametrize(
    "name",
    ["captions.ZH-CN.srt", "captions.zh-Cn.srt", "captions.zh-HANS.srt", "captions.Zh-CN.srt"],
)
def test_a_language_tag_keeps_its_canonical_case(tmp_path: Path, name: str) -> None:
    """Only the case BCP 47 recommends, language lower, script title, region upper, conforms."""
    report = paradigm_report(tmp_path, {**CONFORMING, f"media/{name}": ""})
    assert report["required_gaps"] == [f"repository_paradigm_authored_name:media/{name}"]


def test_a_received_name_keeps_its_upstream_form(tmp_path: Path) -> None:
    """Vendored or generated paths keep their names; a directory of only those keeps its own."""
    files = {
        **CONFORMING,
        "assets/fonts/NotoSansCJKsc-Bold.otf": "",
        "assets/fonts/OFL.txt": "",
        "vendor/JetBrainsMono/OFL.txt": "",
    }
    received = ("assets/fonts/NotoSansCJKsc-Bold.otf", "assets/fonts/OFL.txt")
    report = paradigm_report(tmp_path, files, received=(*received, "vendor/JetBrainsMono/OFL.txt"))
    assert report["verdict"] == "pass", report
    report = paradigm_report(tmp_path, files, received=received)
    assert report["required_gaps"] == [
        "repository_paradigm_authored_name:vendor/JetBrainsMono",
        "repository_paradigm_authored_name:vendor/JetBrainsMono/OFL.txt",
    ]


def test_a_nonconforming_directory_is_reported_once(tmp_path: Path) -> None:
    """Every file below a nonconforming directory shares that directory's single gap."""
    files = {"content/Design_Notes/intro.md": "", "content/Design_Notes/usage.md": ""}
    report = paradigm_report(tmp_path, {**CONFORMING, **files})
    assert report["required_gaps"] == ["repository_paradigm_authored_name:content/Design_Notes"]


@pytest.mark.parametrize(
    "path",
    [
        "src/sample_package/module_name.py",
        "src/sample/py.typed",
        "internal/sample_package/handler_test.go",
        "content/guide/README.md",
        "third/party/LICENSE",
        ".agents/skills/sample-skill/SKILL.md",
        ".config/ci/supply/Dockerfile",
        ".config/ci/supply/Dockerfile.dockerignore",
        ".github/ISSUE_TEMPLATE/task.md",
        ".github/PULL_REQUEST_TEMPLATE.md",
        ".gitlab/merge_request_templates/default.md",
        "tools/raster/Cargo.toml",
        "docs/_meta/taxonomy.toml",
        "src/check.test.mjs",
        ".config/checks/markdownlint-cli2/.markdownlint-cli2.yaml",
        "openspec/changes/archive/2026-01-01-sample/old_notes.md",
        "media/captions.zh-CN.srt",
        "content/narration.pt-BR.txt",
        "media/transcript.zh-Hans-CN.md",
        "content/voice.es-419.txt",
    ],
)
def test_a_name_an_ecosystem_or_tool_fixes_conforms(tmp_path: Path, path: str) -> None:
    """Module, entry, tool-required, marked, suffixed, archived and language-tagged names pass."""
    report = paradigm_report(tmp_path, {**CONFORMING, path: ""})
    assert report["verdict"] == "pass", report


@pytest.mark.parametrize(
    ("path", "gaps"),
    [
        ("rules/module_layout.md", ["repository_paradigm_authored_name:rules/module_layout.md"]),
        ("src/sample_package/module_name.py", []),
        ("content/Design_Notes/intro.md", []),
        ("Makefile", ["repository_paradigm_root_catalog:Makefile"]),
        (
            ".ethos/Legacy_Policy.toml",
            ["repository_paradigm_binding_files:.ethos/Legacy_Policy.toml"],
        ),
    ],
    ids=["new-snake-file", "python-module", "existing-directory", "root-entry", "binding-file"],
)
def test_prewrite_refuses_a_new_nonconforming_basename(path: str, gaps: list[str]) -> None:
    """Prewrite judges the new file's own name; its directories are the report's to judge."""
    assert [gap.required_gap for gap in paradigm_path_gaps(path)] == gaps


def test_prewrite_admits_a_new_received_name() -> None:
    """A new vendored or generated file keeps its upstream name; other obligations still apply."""
    font = "assets/fonts/NotoSansCJKsc-Bold.otf"
    assert [gap.required_gap for gap in paradigm_path_gaps(font)] == [
        f"repository_paradigm_authored_name:{font}"
    ]
    assert paradigm_path_gaps(font, received=True) == ()
    assert [gap.required_gap for gap in paradigm_path_gaps("pytest.ini", received=True)] == [
        "repository_paradigm_root_catalog:pytest.ini"
    ]


def test_a_name_another_obligation_owns_is_reported_once(tmp_path: Path) -> None:
    """Root, binding and configuration names keep their own obligation's single gap."""
    report = paradigm_report(
        tmp_path,
        {**CONFORMING, "CLAUDE.md": "", ".config/checks/Spelling_Rules/policy.toml": ""},
    )
    assert report["required_gaps"] == [
        "repository_paradigm_root_catalog:CLAUDE.md",
        "repository_paradigm_configuration_owner:.config/checks/Spelling_Rules/policy.toml",
    ]


def test_two_forges_without_a_model_are_an_unmodeled_pipeline(tmp_path: Path) -> None:
    """GitLab and GitHub pipelines maintained by hand name the missing CUE model."""
    files = {**CONFORMING, _GITLAB: "", _GITHUB: ""}
    del files[".config/ci/pipeline.cue"]
    files[".config/ci/supply/Dockerfile"] = ""
    report = paradigm_report(tmp_path, files)
    assert report["required_gaps"] == ["repository_paradigm_pipeline_model:.config/ci/"]
    assert report["next_action"] == (
        "define the pipelines once in a .cue model under .config/ci/ and generate "
        "github and gitlab pipeline files from it; check fails when one differs"
    )


@pytest.mark.parametrize(
    ("pipelines", "model"),
    [
        ((_GITLAB, _GITHUB), ".config/ci/pipeline.cue"),
        ((_GITLAB, ".github/workflows/release.yaml"), ".config/ci/peers/gitlab/pipeline.cue"),
        ((_GITLAB,), None),
        ((_GITHUB, ".github/workflows/release.yml"), None),
        ((_GITLAB, ".github/workflows/notes/readme.yml"), None),
    ],
    ids=["model", "nested-model", "gitlab-only", "github-only", "not-a-workflow"],
)
def test_one_forge_or_a_model_needs_no_further_pipeline(
    tmp_path: Path, pipelines: tuple[str, ...], model: str | None
) -> None:
    """A model is needed only when pipelines for more than one Forge are tracked."""
    files = {**CONFORMING, **dict.fromkeys(pipelines, "")}
    del files[".config/ci/pipeline.cue"]
    if model is not None:
        files[model] = ""
    report = paradigm_report(tmp_path, files)
    assert report["verdict"] == "pass", report
