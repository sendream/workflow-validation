"""Read-only current-first lookup for local workflow state migration paths."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CompatibilityLookup:
    path: str
    origin: str
    deprecated: bool
    reason: str
    deprecated_since: str
    remove_after: str


def path_exists(path: Path) -> bool:
    """Treat a symlink itself as present even if its target is currently absent."""

    return path.exists() or path.is_symlink()


def lookup_path(
    current: Path,
    legacy: Path,
    *,
    deprecated_since: str,
    remove_after: str,
) -> CompatibilityLookup:
    """Return one selected path; never merge current and legacy state."""

    current_exists = path_exists(current)
    legacy_exists = path_exists(legacy)
    if current_exists:
        reason = "current path present"
        if legacy_exists:
            reason += "; legacy ignored by current-first precedence"
        return CompatibilityLookup(
            path=str(current),
            origin="current",
            deprecated=False,
            reason=reason,
            deprecated_since=deprecated_since,
            remove_after=remove_after,
        )
    if legacy_exists:
        return CompatibilityLookup(
            path=str(legacy),
            origin="legacy",
            deprecated=True,
            reason="legacy fallback active; migrate to the current path before remove_after",
            deprecated_since=deprecated_since,
            remove_after=remove_after,
        )
    return CompatibilityLookup(
        path=str(current),
        origin="missing",
        deprecated=False,
        reason="neither current nor legacy path exists",
        deprecated_since=deprecated_since,
        remove_after=remove_after,
    )
