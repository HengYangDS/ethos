"""The one GitHub pin of an ETHOS release: its key, both declared forms, lock entries and classes.

Pure functions over text; standard library and `packaging` only, so every layer and the Git hook
path may import it.
"""

from __future__ import annotations

import re
import tomllib
from typing import Any
from typing import Literal
from typing import NamedTuple

from packaging.version import Version

# The distribution identity: the public repository whose release run builds and attests ETHOS.
PIN_REPOSITORY = "HengYangDS/ethos"
PIN_KEY = f"github:{PIN_REPOSITORY}"
# The table that adopters copied before the pin; read only.
LEGACY_KEY = "http:ethos"
PROVENANCE_SETTING = "locked_verify_provenance"
ATTESTED_PROVENANCE = "github-attestations"
SIGNER_WORKFLOW = f"{PIN_REPOSITORY}/.github/workflows/ci.yml"
# The first release whose run attested its archives; earlier releases carry checksums only.
ATTESTED_SINCE = "0.2.0-alpha.29"
# The last release dispatched from `main`; None while every attested release still is.
MAIN_DISPATCH_UNTIL: str | None = None
# Main-dispatched releases whose attestation names another commit than their signed tag.
DIGEST_UNBOUND = frozenset({"0.2.0-beta.3"})

PinForm = Literal["github", "http"]
ReleaseClass = Literal["attested", "attested-main", "checksum"]
_KEYS: dict[PinForm, str] = {"github": PIN_KEY, "http": LEGACY_KEY}
# One release version as `VERSION` spells it; a prefix, a range or `latest` pins nothing exact.
_EXACT = re.compile(r"(?:0|[1-9]\d*)(?:\.(?:0|[1-9]\d*)){2}(?:-(?:alpha|beta|rc)\.(?:0|[1-9]\d*))?")


class DeclaredPin(NamedTuple):
    """The release one Mise configuration selects, and whether it is the exact bare form."""

    form: PinForm
    version: str
    bare: bool
    verify_provenance: bool

    @property
    def key(self) -> str:
        """Name the `[tools]` key that declares this form."""
        return _KEYS[self.form]


class LockEntry(NamedTuple):
    """What a lock records for one platform of the pinned release; "" where it records none."""

    checksum: str
    url: str
    provenance: str


class AttestationIdentity(NamedTuple):
    """The signer, source ref and source commit a release's build attestation must carry."""

    signer_workflow: str
    source_ref: str
    source_digest: str


def exact(version: object) -> bool:
    """Whether a value spells one release exactly as `VERSION` spells it."""
    return isinstance(version, str) and _EXACT.fullmatch(version) is not None


def pin_line(version: str) -> str:
    """Render the one `[tools]` line that `mise use` writes for a release."""
    return f'"{PIN_KEY}" = "{version}"'


def bare_entry(version: str) -> str:
    """Render a whole new configuration that holds only the pin and its setting."""
    return f"[tools]\n{pin_line(version)}\n\n[settings]\n{PROVENANCE_SETTING} = true\n"


def declared_pin(config: str) -> DeclaredPin | None:
    """Read the pin from Mise configuration text in either form; None when it declares none."""
    declared = _document(config, "runtime_pin_invalid")
    tools = _table(declared, "tools")
    found = [form for form, key in _KEYS.items() if key in tools]
    if not found:
        return None
    if len(found) > 1:
        message = "runtime_pin_ambiguous"
        raise ValueError(message)
    value = tools[_KEYS[found[0]]]
    version = value.get("version") if isinstance(value, dict) else value
    if not isinstance(version, str) or not _EXACT.fullmatch(version):
        message = "runtime_pin_invalid"
        raise ValueError(message)
    verified = _table(declared, "settings").get(PROVENANCE_SETTING) is True
    return DeclaredPin(found[0], version, found[0] == "github" and value == version, verified)


def lock_entry(lock: str, pin: DeclaredPin, platform: str) -> LockEntry | None:
    """Read the pinned release's lock entry for one Mise platform; None when it has none."""
    entries = _table(_document(lock, "runtime_pin_lock_invalid"), "tools").get(pin.key)
    for entry in entries if isinstance(entries, list) else ():
        recorded = entry.get(f"platforms.{platform}") if isinstance(entry, dict) else None
        if isinstance(recorded, dict) and entry.get("version") == pin.version:
            return LockEntry._make(str(recorded.get(name, "")) for name in LockEntry._fields)
    return None


def lockfile_version(lock: str) -> int | None:
    """Read the format a lock was written in; a bump stops when a relock would change it."""
    version = _document(lock, "runtime_pin_lock_invalid").get("lockfile_version")
    return version if isinstance(version, int) else None


def release_class(version: str) -> ReleaseClass:
    """Name what a release's published bytes can be verified against."""
    release = Version(version)
    if release < Version(ATTESTED_SINCE) or release in map(Version, DIGEST_UNBOUND):
        return "checksum"
    if MAIN_DISPATCH_UNTIL is None or release <= Version(MAIN_DISPATCH_UNTIL):
        return "attested-main"
    return "attested"


def attestation_identity(version: str, *, tag_commit: str) -> AttestationIdentity | None:
    """Name what the release's attestation must carry; None when only checksums bind it."""
    refs = {"attested": f"refs/tags/v{version}", "attested-main": "refs/heads/main"}
    ref = refs.get(release_class(version))
    return None if ref is None else AttestationIdentity(SIGNER_WORKFLOW, ref, tag_commit)


def _document(text: str, gap: str) -> dict[str, Any]:
    try:
        return tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise ValueError(gap) from error


def _table(document: dict[str, Any], name: str) -> dict[str, Any]:
    """Return one top-level table, empty where the document holds none under that name."""
    table = document.get(name)
    return table if isinstance(table, dict) else {}
