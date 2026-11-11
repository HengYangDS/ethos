"""Read the identity of a repository's protected peers from local Git state only.

A peer is protected when its host is private-class or its `remote.<name>.forgePrivate` is true, and
a remote that marks itself private feeds whether or not the publication declaration names it. Its
feed holds the hosts, ports and namespace paths of its fetch and push URLs and of
`forgeRepository`, the project IDs of the multi-valued `forgeProjectId`, and the former values that
`forgeFormer` records as `host=`, `port=` or `path=`. A clone that cannot know its peers says why:
an invalid publication declaration by its own gaps, a declared peer whose remote holds no URL, or a
feed of nothing. Values never leave the process: callers report counts, forms and positions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ethos.adapters.repo.git import run_git
from ethos.contracts.paradigm.declaration import load_repository_paradigm
from ethos.normalization.coercion import string_sequence
from ethos.repository.paradigm.peer_identity import Feed
from ethos.repository.paradigm.peer_identity import normalized_path
from ethos.repository.release.configuration import release_config
from ethos.repository.release.publication import publication_topology
from ethos.repository.release.publication import topology_remotes

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Mapping
    from pathlib import Path

_URL = re.compile(
    r"[a-z][a-z0-9+.-]*://(?:[^@/]*@)?(\[[^\]]+\]|[^:/]+)(?::(\d+))?(/.*)?$", re.IGNORECASE
)
_SCP = re.compile(r"(?:[^@/]+@)?([^:/]+):(?!//)(.*)$")
_FORGE = re.compile(
    r"remote\.(.+)\.(forgerepository|forgeprojectid|forgeformer|forgeprivate|url|pushurl)"
)
_OPTED = frozenset({"true", "yes", "on", "1"})


@dataclass(frozen=True, slots=True)
class LocalFeed:
    """What a clone knows of its protected peers: their feed, and why it may not be complete."""

    feed: Feed
    gaps: tuple[str, ...]

    def __bool__(self) -> bool:
        return bool(self.feed)


def local_feed(root: Path) -> LocalFeed:
    """Return the protected peers' feed with the gaps that keep the clone from knowing it whole.

    An invalid publication declaration names itself; else each declared peer whose remote holds
    no URL; else a feed of nothing. An unread peer comes first, since it may be the protected one.
    """
    try:
        topology = publication_topology(root, release_config(root))
    except ValueError as error:
        topology = {"required_gaps": [str(error)]}
    declared = tuple(topology_remotes(topology).values())
    keys = _forge_keys(root)
    opted = (remote for remote, held in keys.items() if remote not in declared and _opted(held))
    remotes = (*declared, *opted)
    urls = {remote: _urls(root, remote) for remote in remotes}
    protected = [remote for remote in remotes if _protected(urls[remote], keys.get(remote, {}))]
    feed = feed_from_config(
        {remote: {**keys.get(remote, {}), "url": urls[remote]} for remote in protected}
    )
    declaration = tuple(string_sequence(topology.get("required_gaps")))
    unread = tuple(
        f"peer_identity_feed_unreadable:{remote}"
        for remote in declared
        if not _holds_url(keys.get(remote, {}))
    )
    return LocalFeed(feed, declaration or unread or (() if feed else ("peer_identity_feed_empty",)))


def feed_from_config(remotes: Mapping[str, Mapping[str, Iterable[str]]]) -> Feed:
    """Build the feed of the named remotes from their URLs and forge keys."""
    hosts: set[str] = set()
    ports: set[int] = set()
    paths: set[str] = set()
    ids: set[int] = set()
    for config in remotes.values():
        for url in (*config.get("url", ()), *config.get("forgerepository", ())):
            host, port, path = remote_parts(url)
            hosts.update((host,) if host else ())
            ports.update((int(port),) if port else ())
            paths.update((path,) if path else ())
        ids.update(int(value) for value in config.get("forgeprojectid", ()) if value.isdigit())
        for value in config.get("forgeformer", ()):
            field, _sep, item = value.partition("=")
            if field == "host" and item:
                hosts.add(item.lower())
            elif field == "port" and item.isdigit():
                ports.add(int(item))
            elif field == "path" and item:
                paths.add(normalized_path(item))
    return Feed.of(hosts=hosts, ports=ports, paths=paths, ids=ids)


def remote_parts(url: str) -> tuple[str, str, str]:
    """Return the host, port and namespace path of one remote URL in URL or scp form."""
    match = _URL.match(url)
    if match:
        host = match.group(1).strip("[]").lower()
        return host, match.group(2) or "", normalized_path(match.group(3) or "")
    match = _SCP.match(url)
    if match:
        return match.group(1).lower(), "", normalized_path(match.group(2))
    return "", "", ""


def _protected(urls: Iterable[str], keys: Mapping[str, Iterable[str]]) -> bool:
    paradigm = load_repository_paradigm()
    hosts = (host for host, _port, _path in map(remote_parts, urls) if host)
    return _opted(keys) or any(paradigm.names_private_address(f"//{host}") for host in hosts)


def _opted(keys: Mapping[str, Iterable[str]]) -> bool:
    """Return whether a remote marks itself private with `forgePrivate`."""
    return any(value.lower() in _OPTED for value in keys.get("forgeprivate", ()))


def _holds_url(keys: Mapping[str, Iterable[str]]) -> bool:
    """Return whether a remote holds a URL; as in Git, an empty value clears the earlier ones."""
    for name in ("url", "pushurl"):
        held: list[str] = []
        for value in keys.get(name, ()):
            held = [*held, value] if value else []
        if held:
            return True
    return False


def _urls(root: Path, remote: str) -> tuple[str, ...]:
    """Return a remote's fetch and push URLs as Git rewrites them, or none for no such remote."""
    found: list[str] = []
    for push in ((), ("--push",)):
        listed = run_git(root, "remote", "get-url", *push, "--all", remote, check=False)
        if listed.returncode == 0:
            found.extend(line for line in listed.stdout.splitlines() if line)
    return tuple(dict.fromkeys(found))


def _forge_keys(root: Path) -> dict[str, dict[str, list[str]]]:
    """Return each remote's forge and URL keys; Git lowers their names, never the remote's."""
    pattern = r"^remote\..*\.(forge.*|url|pushurl)$"
    listed = run_git(root, "config", "-z", "--get-regexp", pattern, check=False)
    keys: dict[str, dict[str, list[str]]] = {}
    for entry in listed.stdout.split("\0") if listed.returncode == 0 else ():
        name, _newline, value = entry.partition("\n")
        match = _FORGE.fullmatch(name)
        if match:
            keys.setdefault(match.group(1), {}).setdefault(match.group(2), []).append(value)
    return keys


def ci_feed(environ: Mapping[str, str]) -> Feed:
    """Build the feed a GitLab job exposes about its own project; empty outside such a job."""
    host = environ.get("CI_SERVER_HOST", "")
    port = environ.get("CI_SERVER_PORT", "")
    project = environ.get("CI_PROJECT_ID", "")
    return Feed.of(
        hosts=(host,) if host else (),
        ports=(int(port),) if port.isdigit() else (),
        paths=(environ["CI_PROJECT_PATH"],) if environ.get("CI_PROJECT_PATH") else (),
        ids=(int(project),) if project.isdigit() else (),
    )
