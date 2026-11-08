"""Read the identity of a repository's protected release peers from local Git state only.

A peer is protected when its host is private-class or its `remote.<name>.forgePrivate` is true.
Its feed holds the hosts, ports and namespace paths of its fetch and push URLs and of
`forgeRepository`, the project IDs of the multi-valued `forgeProjectId`, and the former values that
`forgeFormer` records as `host=`, `port=` or `path=`. Values never leave the process: callers report
counts, forms and positions.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from ethos.adapters.repo.git import run_git
from ethos.contracts.paradigm.declaration import load_repository_paradigm
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
_FORGE = re.compile(r"remote\.(.+)\.(forgerepository|forgeprojectid|forgeformer|forgeprivate)")


def peer_feed(root: Path) -> Feed:
    """Return the identity that the protected release peers of a repository declare."""
    remotes = topology_remotes(publication_topology(root, release_config(root))).values()
    keys = _forge_keys(root)
    urls = {remote: _urls(root, remote) for remote in remotes}
    protected = [remote for remote in remotes if _protected(urls[remote], keys.get(remote, {}))]
    return feed_from_config(
        {remote: {**keys.get(remote, {}), "url": urls[remote]} for remote in protected}
    )


def feed_from_config(remotes: Mapping[str, Mapping[str, Iterable[str]]]) -> Feed:
    """Build the feed of the named remotes from their URLs and forge keys."""
    hosts: set[str] = set()
    ports: set[int] = set()
    paths: set[str] = set()
    ids: set[int] = set()
    for config in remotes.values():
        for url in config.get("url", ()):
            host, port, path = remote_parts(url)
            hosts.update((host,) if host else ())
            ports.update((int(port),) if port else ())
            paths.update((path,) if path else ())
        paths.update(normalized_path(value) for value in config.get("forgerepository", ()))
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
    opted = any(
        value.lower() in {"true", "yes", "on", "1"} for value in keys.get("forgeprivate", ())
    )
    return opted or any(paradigm.names_private_address(f"//{host}") for host in hosts)


def _urls(root: Path, remote: str) -> tuple[str, ...]:
    """Return a remote's fetch and push URLs as Git rewrites them, or none for no such remote."""
    found: list[str] = []
    for push in ((), ("--push",)):
        listed = run_git(root, "remote", "get-url", *push, "--all", remote, check=False)
        if listed.returncode == 0:
            found.extend(line for line in listed.stdout.splitlines() if line)
    return tuple(dict.fromkeys(found))


def _forge_keys(root: Path) -> dict[str, dict[str, list[str]]]:
    """Return each remote's forge keys; Git lowers their names, never the remote's."""
    listed = run_git(root, "config", "-z", "--get-regexp", r"^remote\..*\.forge", check=False)
    keys: dict[str, dict[str, list[str]]] = {}
    for entry in listed.stdout.split("\0") if listed.returncode == 0 else ():
        name, _newline, value = entry.partition("\n")
        match = _FORGE.fullmatch(name)
        if match:
            keys.setdefault(match.group(1), {}).setdefault(match.group(2), []).append(value)
    return keys
