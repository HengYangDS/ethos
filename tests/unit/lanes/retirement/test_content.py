"""Reviewed retirement inventory rejects foreign, replaced and unobservable content."""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

import ethos.adapters.mutation.lane_retirement.content as content
import ethos.adapters.mutation.lane_retirement.operation as operation
from tests.support.governed_repository import git
from tests.support.lane_scenarios import derive_abandonment


@pytest.mark.parametrize("boundary", ["root", "parent"])
def test_reviewed_inventory_never_opens_through_replaced_parent(
    divergent_lane, monkeypatch, boundary
):
    repo, lane = divergent_lane
    nested = lane / "nested"
    nested.mkdir()
    (nested / "material.txt").write_text("reviewed local bytes\n")
    selected = lane if boundary == "root" else nested
    retained = selected.with_name(f"{selected.name}-retained")
    external = repo.parent / "external"
    external_file = external / ("nested/material.txt" if boundary == "root" else "material.txt")
    external_file.parent.mkdir(parents=True)
    external_file.write_text("unrelated private bytes\n")
    external_identity = external_file.stat()
    native_open = os.open
    opened_external = []
    swapped = False

    def replace_before_open(path, flags, *args, **kwargs):
        nonlocal swapped
        if Path(path).name == "material.txt" and not swapped:
            selected.rename(retained)
            selected.symlink_to(external, target_is_directory=True)
            swapped = True
        descriptor = native_open(path, flags, *args, **kwargs)
        observed = os.fstat(descriptor)
        if (observed.st_dev, observed.st_ino) == (
            external_identity.st_dev,
            external_identity.st_ino,
        ):
            opened_external.append(str(path))
        return descriptor

    monkeypatch.setattr(content.os, "open", replace_before_open)
    before = git(repo, "show-ref")
    try:
        result = derive_abandonment(repo, review_content=True)
    finally:
        if swapped:
            selected.unlink()
            retained.rename(selected)

    assert swapped, "fault did not reach the content observer"
    assert not opened_external, opened_external
    assert result["verdict"] == "block", result
    assert result["required_gaps"] == ["retirement_content_drift"]
    assert external_file.read_text() == "unrelated private bytes\n"
    assert git(repo, "show-ref") == before
    assert not operation.operation_store(repo).exists()


@pytest.mark.parametrize("boundary", ["root", "directory", "file", "index"])
@pytest.mark.parametrize("coordinate", ["st_uid", "st_dev"])
def test_reviewed_inventory_rejects_foreign_native_nodes_before_reading(
    divergent_lane, monkeypatch, boundary, coordinate
):
    repo, lane = divergent_lane
    directory = lane / "nested"
    directory.mkdir()
    selected = {
        "root": lane,
        "directory": directory,
        "file": lane / "abandoned.txt",
        "index": Path(git(lane, "rev-parse", "--path-format=absolute", "--git-path", "index")),
    }[boundary]
    identity = selected.stat()
    native_stat, native_fstat, native_open = os.stat, os.fstat, os.open
    opened = []

    def observed(value):
        if (value.st_dev, value.st_ino) != (identity.st_dev, identity.st_ino):
            return value
        fields = {name: getattr(value, name) for name in dir(value) if name.startswith("st_")}
        fields[coordinate] += 1
        return SimpleNamespace(**fields)

    def observe_open(*args, **kwargs):
        descriptor = native_open(*args, **kwargs)
        value = native_fstat(descriptor)
        if (value.st_dev, value.st_ino) == (identity.st_dev, identity.st_ino):
            opened.append(descriptor)
        return descriptor

    monkeypatch.setattr(content.os, "stat", lambda *a, **kw: observed(native_stat(*a, **kw)))
    monkeypatch.setattr(content.os, "fstat", lambda fd: observed(native_fstat(fd)))
    monkeypatch.setattr(content.os, "open", observe_open)
    before = git(repo, "show-ref")

    result = derive_abandonment(repo, review_content=True)

    assert result["verdict"] == "block", result
    assert result["required_gaps"] == [
        "retirement_content_owner_mismatch"
        if coordinate == "st_uid"
        else "retirement_content_filesystem_mismatch"
    ]
    assert not opened, "the observer entered or read a foreign node"
    assert git(repo, "show-ref") == before
    assert (lane / "abandoned.txt").read_text() == "abandoned\n"
    assert not operation.operation_store(repo).exists()


def test_reviewed_inventory_preserves_literal_link_without_opening_target(divergent_lane):
    repo, lane = divergent_lane
    external = repo.parent / "external.txt"
    external.write_text("unrelated data\n")
    literal = ".././external.txt"
    (lane / "external-link").symlink_to(literal)

    result = derive_abandonment(repo, review_content=True)

    assert result["verdict"] == "pass", result
    receipt = result["receipt"]
    assert isinstance(receipt, dict)
    request = operation.load_operation(repo, receipt["path"], receipt["sha256"])
    observed = request.reviewed_content["entries"]["external-link"]
    assert observed["kind"] == "symlink"
    assert observed["target"] == literal
    assert "sha256" not in observed
    assert external.read_text() == "unrelated data\n"


@pytest.mark.parametrize("fault", ["unavailable", "enumeration", "nested", "fifo"])
def test_reviewed_inventory_rejects_incomplete_or_unsafe_observation(
    divergent_lane, monkeypatch, fault
):
    repo, lane = divergent_lane
    if fault == "unavailable":
        monkeypatch.delattr(content.os, "fwalk")
    elif fault == "enumeration":

        def fail_walk(*_args, onerror, **_kwargs):
            onerror(PermissionError("selected_directory_unreadable"))
            return iter(())

        monkeypatch.setattr(content.os, "fwalk", fail_walk)
    elif fault == "nested":
        (lane / "nested/.git").mkdir(parents=True)
    else:
        os.mkfifo(lane / "pipe")
    before = git(repo, "show-ref")

    result = derive_abandonment(repo, review_content=True)

    assert result["verdict"] == "block", result
    assert result["required_gaps"] == [
        {
            "unavailable": "retirement_content_observation_unavailable",
            "enumeration": "selected_directory_unreadable",
            "nested": "retirement_nested_repository",
            "fifo": "retirement_content_unsafe",
        }[fault]
    ]
    assert git(repo, "show-ref") == before
    assert (lane / "abandoned.txt").read_text() == "abandoned\n"
    assert not operation.operation_store(repo).exists()
