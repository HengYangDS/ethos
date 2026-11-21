"""Repository-authored names and the multi-Forge pipeline model."""

from __future__ import annotations

from itertools import starmap
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.admission.paths import check_write_paths
from ethos.repository.paradigm.names import IdentifierNames
from ethos.repository.paradigm.report import paradigm_path_gaps
from tests.support.governed_repository import git
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
        "or linguist-generated in .gitattributes if it is third-party or generated, or declare "
        "the tracked manifest that repeats it under identifier_sources in .ethos/profile.toml "
        "if an upstream contract fixes the name"
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
        "crates/channel_solver/src/flow_graph.rs",
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
        tmp_path, {**CONFORMING, "CLAUDE.md": "", ".config/checks/Spelling_Rules/policy.toml": ""}
    )
    assert report["required_gaps"] == [
        "repository_paradigm_root_catalog:CLAUDE.md",
        "repository_paradigm_configuration_owner:.config/checks/Spelling_Rules/policy.toml",
    ]


_PROFILE = ".ethos/profile.toml"
_SOURCE = '\n[[identifier_sources]]\nmanifests = "{}"\nkeys = ["{}"]\nvalues = "{}"\n'
_SOURCES = [
    ("**/product.toml", "product.id", "whole"),
    ("**/product.toml", "queries.sql.*", "path"),
    ("data/**/catalog.json", "products.*.query_name", "whole"),
    ("**/bundle.toml", "bundle.namespace", "dotted"),
]
_BUNDLE = "data/a_index/bundle.toml"
_PRODUCT = "data/a_index/Daily_Close/product.toml"
_QUERY = "data/a_index/Daily_Close/Shared_Sql/pre_start.mssql.sql"
_CATALOG = "data/sql/catalog.json"
_IDENTIFIED = {
    **CONFORMING,
    _PROFILE: CONFORMING[_PROFILE] + "".join(starmap(_SOURCE.format, _SOURCES)),
    _BUNDLE: '[bundle]\nnamespace = "core.a_index"\n',
    _PRODUCT: '[product]\nid = "Daily_Close"\n\n[[queries]]\n'
    'sql = {mssql = "Shared_Sql/pre_start.mssql.sql"}\n',
    _QUERY: "",
    _CATALOG: '{"products": {"one": {"query_name": ["used_sql"]}}}\n',
    "data/sql/used_sql.sql": "",
}
_ADMISSIONS = [
    {"name": path.rsplit("/", 1)[-1], "carrier": path, "manifest": manifest}
    for path, manifest in [
        ("data/a_index", _BUNDLE),
        (_PRODUCT[:-13], _PRODUCT),
        (_QUERY[:-20], _PRODUCT),
        (_QUERY, _PRODUCT),
        ("data/sql/used_sql.sql", _CATALOG),
    ]
]
_NAME_GAPS = [f"repository_paradigm_authored_name:{row['carrier']}" for row in _ADMISSIONS]
_SOURCE_GAP = "repository_paradigm_identifier_source:"
_ALL = [0, 1, 2, 3, 4]
_KEY_GAPS = [
    f"{_SOURCE_GAP}{_PROFILE}:identifier_sources.{glob}:{key}" for glob, key, _values in _SOURCES
]


def test_a_name_a_declared_manifest_key_repeats_is_admitted_with_its_evidence(
    tmp_path: Path,
) -> None:
    """A directory, a file stem, a dotted part and a path segment pass, each with its manifest.

    An array of strings holds one identifier per element, as the catalog's query names do.
    """
    report = paradigm_report(tmp_path / "declared", _IDENTIFIED)
    assert (report["verdict"], report["name_admissions"]) == ("pass", _ADMISSIONS), report
    others = {"data/a_index/Weekly_Close/notes.md": "", "data/sql/unused_sql.sql": ""}
    report = paradigm_report(tmp_path / "others", {**_IDENTIFIED, **others})
    assert report["required_gaps"] == [
        "repository_paradigm_authored_name:data/a_index/Weekly_Close",
        "repository_paradigm_authored_name:data/sql/unused_sql.sql",
    ]
    report = paradigm_report(tmp_path / "plain", {**_IDENTIFIED, _PROFILE: CONFORMING[_PROFILE]})
    assert (report["required_gaps"], report["name_admissions"]) == (_NAME_GAPS, [])


@pytest.mark.parametrize(
    ("files", "untracked", "sources", "names"),
    [
        ({_BUNDLE: '[bundle]\nnamespace = "core"\n'}, (), [], [0]),
        ({_BUNDLE: ""}, (), _KEY_GAPS[3:], [0]),
        ({}, (_BUNDLE,), _KEY_GAPS[3:], [0]),
        ({_CATALOG: "{"}, (), [_SOURCE_GAP + _CATALOG, _KEY_GAPS[2]], [4]),
        (
            {_CATALOG: '{"products": {"one": {"query_name": "a/b"}, "two": 2}}'},
            (),
            _KEY_GAPS[2:3],
            [4],
        ),
        ({_PRODUCT: '[product]\nid = ""\nqueries = [{sql = 1}]\n'}, (), _KEY_GAPS[:2], [1, 2, 3]),
        ({"docs/product.toml": "\xff"}, (), [f"{_SOURCE_GAP}docs/product.toml"], []),
        ({_PROFILE: _IDENTIFIED[_PROFILE] + _SOURCE.format("**", "", "whole")}, (), [], _ALL),
        ({_PROFILE: _IDENTIFIED[_PROFILE] + _SOURCE.format("**", "id", "stem")}, (), [], _ALL),
    ],
    ids=[
        *("other-value", "no-key", "no-manifest", "unparsable", "slash", "empty"),
        *("one-unreadable", "empty-key", "unknown-reading"),
    ],
)
def test_an_identifier_source_without_evidence_excuses_nothing(
    tmp_path: Path,
    files: dict[str, str],
    untracked: tuple[str, ...],
    sources: list[str],
    names: list[int],
) -> None:
    """A source no file matches, a key no manifest carries and an unreadable manifest are gaps.

    A profile with an invalid source row is its owner's gap and admits nothing.
    """
    report = paradigm_report(tmp_path, {**_IDENTIFIED, **files}, untracked=untracked)
    # The source gap is new in this release, so it reports; the names it excuses nothing for block.
    assert report["reported_gaps"] == sources
    assert report["required_gaps"] == [_NAME_GAPS[index] for index in names]


def test_prewrite_admits_a_new_file_stem_a_tracked_manifest_repeats(tmp_path: Path) -> None:
    """The single-path judgment reads the same evidence, lazily, from the tracked manifests."""
    new, other = "data/sql/used_sql.mysql.sql", "data/sql/unused_sql.sql"
    gap = f"repository_paradigm_authored_name:{new}"
    assert [item.required_gap for item in paradigm_path_gaps(new)] == [gap]
    evidence = IdentifierNames({"used_sql": _CATALOG}, [], [])
    assert paradigm_path_gaps(new, identifiers=lambda: evidence) == ()
    paradigm_report(tmp_path, _IDENTIFIED)
    git(tmp_path, "init", "--quiet")
    paths = [tmp_path / new, tmp_path / other]
    checked = check_write_paths(tmp_path, paths, "work", effect_report={})[0]
    assert [item["reason"] for item in checked] == [gap, gap.replace(new, other)]
    git(tmp_path, "add", _PROFILE, _CATALOG)
    checked = check_write_paths(tmp_path, paths, "work", effect_report={})[0]
    assert [item["reason"] for item in checked] == ["allowed", gap.replace(new, other)]


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
