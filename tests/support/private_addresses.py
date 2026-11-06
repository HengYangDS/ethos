"""Address fixtures for the private-address boundary.

Tracked text names no private-class literal, so each private fixture is joined when it is used. The
private ones are neutral examples of their class, never a real peer's address.
"""

from __future__ import annotations

import hashlib
import hmac


def _ipv4(*octets: int) -> str:
    """Join octets when used, so tracked text names no literal of a private class."""
    return ".".join(map(str, octets))


PRIVATE_FORGE = _ipv4(192, 168, 0, 10) + ":8080"
INTERNAL_FORGE = "forge." + "internal:8080"
DOCUMENTATION_FORGE = "192.0.2.1:8080"


def redaction_marker(literal: str, key: bytes) -> str:
    """Return the redaction marker that an immutable record carries in place of a literal."""
    digest = hmac.new(key, literal.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"[redacted:private-network-address:hmac-sha256:{digest}]"


# One line each, so a native scan's line numbers identify the case.
PRIVATE_TEXTS = {
    "private-forge-url": f"remote http://{PRIVATE_FORGE}/team/repo",
    "rfc1918-bare": "host " + _ipv4(10, 1, 2, 3) + " is up",
    "rfc1918-upper-edge": "[" + _ipv4(172, 31, 255, 1) + "]",
    "sentence-end": "the forge is at " + _ipv4(10, 0, 0, 9) + ".",
    "unique-local-v6": "http://[" + "fd12" + ":3456::1]:8080/",
    "internal-port": f"http://{INTERNAL_FORGE}/team/repo",
    "lan-scp": "git@forge." + "lan:group/repo.git",
    "local-url": "https://ethos." + "local/schemas/result.schema.json",
    "home-arpa": "ssh://nas.home." + "arpa/volume",
    "upper-case": "HTTP://FORGE." + "INTERNAL:80/",
    "merge-request-url": f"See merge request http://{INTERNAL_FORGE}/group/project!7",
}
DOCUMENTATION_TEXTS = {
    "documentation": f"remote http://{DOCUMENTATION_FORGE}/team/repo at forge.example.invalid",
    "documentation-v6": "http://[2001:db8::1]:8080/",
    "reserved-names": "http://forge.test:8080/team/repo and https://example.com",
    "public-identity": "https://github.com/HengYangDS/ethos and ghcr.io/hengyangds/ethos-supply",
    "merge-path": "See merge request dig/research/team/ethos!7",
    "attributes": "if version.local:\n    threading.local()\nself.lan = 1",
    "file-names": ".claude/settings.local.json and tools/ci/docker-compose.local-ci.yml",
    "versions": "v10.0.0.1-rc1, 1.10.0.0.1 and 10.0.19041.1",
    "slices": "a[::1] b[::-1] std::1",
    "classes-in-prose": "RFC 1918 covers 10/8, 172.16/12 and 192.168/16; ULA is fc00::/7",
    "public-neighbours": "8.8.8.8, 172.32.0.1, 192.169.1.1 and 11.0.0.1",
    "digest": "sha256:fd12ab34cd56ef7890",
    "localhost": "localhost:8080 and ('localhost', 0)",
    # Loopback and link-local literals disclose no peer, so they pass outside ETHOS's surfaces.
    "loopback": '("' + _ipv4(127, 0, 0, 1) + '", 0)',
    "link-local": "addr=" + _ipv4(169, 254, 1, 1),
    "link-local-v6": "fe" + "80::1%en0",
    "loopback-v6": "http://[" + ":" + ":1]:9/",
    "redaction": redaction_marker(PRIVATE_FORGE, b"record owner key"),
}
