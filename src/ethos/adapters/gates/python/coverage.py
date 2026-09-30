"""Observe native coverage without replaying the workload that produced it."""

from __future__ import annotations

import hashlib
import json
import tomllib
from dataclasses import asdict
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from ethos.adapters.gates.verification import NativePackageSources
from ethos.adapters.process import run_command
from ethos.adapters.repo.git import git_files

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.adapters.gates.verification import NativePythonReports


_BUILD_PROJECTION = """
import json,sys
from hatchling.builders.wheel import WheelBuilder
builder = WheelBuilder(root=sys.argv[1])
print(json.dumps({
    'distribution': builder.metadata.core.name,
    'members': [[item.path, item.relative_path, item.distribution_path]
                for item in builder.recurse_included_files()]
}))
"""


_COVERAGE_OBSERVATION = """
import base64,hashlib,io,json,re,sys,zipfile
from importlib import metadata
from pathlib import Path,PurePosixPath
from urllib.parse import urlsplit
from urllib.request import url2pathname
import coverage


def invalid(reason):
    raise ValueError('python_native_' + reason)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def installed_source(path, package, sources, locations, artifacts):
    if package is None:
        return None
    for source, member in package['members']:
        parts = PurePosixPath(member).parts
        if tuple(path.parts[-len(parts):]) != parts:
            continue
        base = path.parents[len(parts) - 1]
        if base not in locations:
            locations[base] = tuple(metadata.distributions(path=[str(base)]))
        for distribution in locations[base]:
            name = re.sub(r'[-_.]+', '-', distribution.metadata['Name']).lower()
            if name != re.sub(r'[-_.]+', '-', package['distribution']).lower():
                continue
            files = {str(item): item for item in distribution.files or ()}
            located = (Path(distribution.locate_file(files[member])).resolve()
                       if member in files else None)
            if located != path:
                continue
            direct = distribution.read_text('direct_url.json')
            if direct is None:
                invalid('artifact_provenance_missing')
            direct = json.loads(direct)
            url = urlsplit(direct.get('url', ''))
            if url.scheme != 'file' or url.netloc or 'dir_info' in direct:
                invalid('artifact_provenance_unsupported')
            artifact = Path(url2pathname(url.path))
            if artifact.is_symlink() or not artifact.is_file() or artifact.suffix != '.whl':
                invalid('artifact_unavailable')
            artifact_bytes = artifact.read_bytes()
            artifact_digest = hashlib.sha256(artifact_bytes).hexdigest()
            try:
                with zipfile.ZipFile(io.BytesIO(artifact_bytes)) as wheel:
                    names = wheel.namelist()
                    if len(names) != len(set(names)):
                        invalid('artifact_members_ambiguous')
                    for original, included in package['members']:
                        item = files.get(included)
                        if item is None or included not in names or original not in sources:
                            invalid('artifact_source_scope_incomplete')
                        installed = Path(distribution.locate_file(item))
                        if installed.is_symlink() or not installed.is_file():
                            invalid('source_identity_unavailable')
                        source_digest = sources[original]
                        value = installed.read_bytes()
                        hashed = hashlib.sha256(value)
                        if hashed.hexdigest() != source_digest:
                            invalid('source_identity_mismatch')
                        record_digest = base64.urlsafe_b64encode(hashed.digest()).decode()
                        if (item.hash is None or item.hash.mode != 'sha256'
                                or item.hash.value != record_digest.rstrip('=')):
                            invalid('artifact_record_mismatch')
                        if hashlib.sha256(wheel.read(included)).hexdigest() != source_digest:
                            invalid('artifact_source_mismatch')
            except zipfile.BadZipFile:
                invalid('artifact_unreadable')
            artifacts[str(artifact.resolve())] = {
                'path': str(artifact.resolve()), 'sha256': artifact_digest,
                'distribution': package['distribution'],
                'binding': 'observed-wheel-member-and-source-bytes',
            }
            return source
    return None


def observe(inputs):
    root, output = Path(inputs['root']).resolve(), Path(inputs['output']).resolve()
    sources = dict(inputs['source_digests'])
    package = inputs['packaged_sources']
    for source, expected in sources.items():
        if digest(root / source) != expected:
            invalid('source_inputs_changed')
    if package is not None:
        for path, expected in package['input_digests']:
            if digest(root / path) != expected:
                invalid('artifact_build_inputs_changed')
    native = coverage.Coverage(data_file=str(output / '.coverage'), config_file=False)
    native.combine(data_paths=[str(output)], strict=True, keep=True)
    native.load()
    data = native.get_data()
    if not data.has_arcs():
        invalid('source_branch_evidence_missing')
    checkout = {(root / source).resolve(): source for source in inputs['source']}
    paths, locations, artifacts = {}, {}, {}
    for observed in data.measured_files():
        path = Path(observed).resolve()
        source = checkout.get(path)
        if source is None and data.lines(observed):
            source = installed_source(path, package, sources, locations, artifacts)
        if source is not None:
            paths[observed] = str(root / source)
    report = coverage.Coverage(data_file=None, config_file=False)
    report.clear_exclude('exclude')
    report.clear_exclude('partial')
    report.get_data().update(data, map_path=lambda path: paths.get(path, path))
    session_reports = []
    for session in inputs['sessions']:
        report.get_data().set_query_context(session)
        exercised = []
        for source in inputs['source']:
            absolute = str(root / source)
            if not report.analysis2(absolute)[1]:
                continue
            if report.get_data().lines(absolute):
                exercised.append(source)
        if not set(exercised) - set(inputs['orchestrators']):
            invalid('session_source_execution_missing:' + session)
        session_reports.append({'id': session, 'covered_paths': exercised})
    report.get_data().set_query_contexts(None)
    non_applicable = []
    for source in inputs['source']:
        absolute = str(root / source)
        statements = report.analysis2(absolute)[1]
        if not statements:
            non_applicable.append(source)
        elif not report.get_data().lines(absolute):
            invalid('source_unexercised:' + source)
    target = output / 'coverage-source.json'
    report.json_report(
        morfs=[str(root / source) for source in inputs['source']], outfile=str(target)
    )
    result = json.loads(target.read_text())
    totals = result['totals']
    covered = totals['covered_lines'] + totals['covered_branches']
    if covered == 0:
        invalid('source_execution_missing')
    return {
        'covered': covered, 'measured': totals['num_statements'] + totals['num_branches'],
        'branch_coverage': result['meta']['branch_coverage'],
        'selected_paths': inputs['source'], 'non_applicable_paths': non_applicable,
        'artifacts': list(artifacts.values()), 'files': result['files'],
        'sessions': session_reports,
    }


try:
    print(json.dumps({'result': observe(json.load(sys.stdin))}))
except (OSError, ValueError, KeyError, TypeError, coverage.CoverageException) as error:
    message = (str(error) if isinstance(error, ValueError)
               else 'python_native_source_observation_invalid')
    print(json.dumps({'error': message}))
"""


def _native_json(
    root: Path,
    prefix: tuple[str, ...],
    probe: str,
    *,
    arguments: tuple[str, ...] = (),
    payload: str = "",
) -> dict[str, object]:
    """Query the selected native tool supply without importing consumer source."""
    result = run_command(
        root, (*prefix, "-B", "-I", "-c", probe, *arguments), stdin=payload, timeout=30
    )
    if result.returncode:
        message = "python_native_source_observer_unavailable"
        raise ValueError(message)
    value = json.loads(result.stdout)
    if not isinstance(value, dict):
        message = "python_native_source_observation_invalid"
        raise TypeError(message)
    if "error" in value:
        raise ValueError(str(value["error"]))
    return value


def artifact_sources(root: Path, python_prefix: tuple[str, ...]) -> NativePackageSources | None:
    """Hold the selected native build's source correspondence before execution."""
    configuration = root / "pyproject.toml"
    if not configuration.is_file():
        return None
    project = tomllib.loads(configuration.read_text(encoding="utf-8"))
    build = project.get("build-system", {})
    if not isinstance(build, dict) or build.get("build-backend") != "hatchling.build":
        return None
    projection = _native_json(root, python_prefix, _BUILD_PROJECTION, arguments=(str(root),))
    distribution, values = projection.get("distribution"), projection.get("members")
    if not isinstance(distribution, str) or not distribution or not isinstance(values, list):
        message = "python_native_artifact_projection_invalid"
        raise ValueError(message)
    tracked = set(git_files(root))
    members: list[tuple[str, str]] = []
    for item in values:
        if (
            not isinstance(item, list)
            or len(item) != 3
            or not all(isinstance(v, str) for v in item)
        ):
            message = "python_native_artifact_projection_invalid"
            raise ValueError(message)
        absolute, relative, included = item
        if not included.endswith(".py"):
            continue
        if (
            relative not in tracked
            or (root / relative).is_symlink()
            or (root / relative).resolve().as_posix() != absolute
            or PurePosixPath(included).is_absolute()
            or ".." in PurePosixPath(included).parts
        ):
            message = "python_native_artifact_source_scope_invalid"
            raise ValueError(message)
        members.append((relative, included))
    if len({included for _, included in members}) != len(members):
        message = "python_native_artifact_members_ambiguous"
        raise ValueError(message)
    inputs = tuple(path for path in ("pyproject.toml", "hatch.toml") if path in tracked)
    return NativePackageSources(
        distribution=distribution,
        members=tuple(members),
        input_digests=tuple(
            (path, hashlib.sha256((root / path).read_bytes()).hexdigest()) for path in inputs
        ),
    )


def observe(
    root: Path,
    inputs: NativePythonReports,
    source: tuple[str, ...],
    *,
    sessions: tuple[str, ...] = (),
    orchestrators: tuple[str, ...] = (),
) -> dict[str, object]:
    """Account for executed source identities, including native installed artifacts."""
    payload = json.dumps(
        {
            "root": str(root),
            "output": str(inputs.root),
            "source": source,
            "sessions": sessions,
            "orchestrators": orchestrators,
            "source_digests": inputs.source_digests,
            "packaged_sources": (
                asdict(inputs.packaged_sources) if inputs.packaged_sources is not None else None
            ),
        }
    )
    value = _native_json(root, inputs.python_prefix, _COVERAGE_OBSERVATION, payload=payload)
    result = value.get("result")
    if not isinstance(result, dict):
        message = "python_native_source_observation_invalid"
        raise TypeError(message)
    return result
