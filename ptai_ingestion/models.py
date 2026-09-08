"""Lifecycle names and transition validation for cataloged sources."""

from enum import StrEnum


class Lifecycle(StrEnum):
    NEW = "new"
    VERIFIED = "verified"
    APPROVED = "approved"
    ACQUIRED = "acquired"
    EXTRACTED = "extracted"
    INDEXED = "indexed"
    CATALOGED = "cataloged"
    DUPLICATE = "duplicate"
    NEEDS_REVIEW = "needs_review"
    RIGHTS_HOLD = "rights_hold"
    EXTRACTION_FAILED = "extraction_failed"
    TRANSCRIPTION_FAILED = "transcription_failed"
    INDEXING_FAILED = "indexing_failed"
    UNAVAILABLE = "unavailable"


TERMINAL_HOLDS = {Lifecycle.NEEDS_REVIEW, Lifecycle.RIGHTS_HOLD}
TRANSITIONS: dict[Lifecycle, set[Lifecycle]] = {
    Lifecycle.NEW: {Lifecycle.VERIFIED, Lifecycle.NEEDS_REVIEW, Lifecycle.RIGHTS_HOLD, Lifecycle.DUPLICATE},
    Lifecycle.VERIFIED: {Lifecycle.APPROVED, Lifecycle.NEEDS_REVIEW, Lifecycle.RIGHTS_HOLD, Lifecycle.DUPLICATE},
    Lifecycle.APPROVED: {Lifecycle.ACQUIRED, Lifecycle.NEEDS_REVIEW, Lifecycle.RIGHTS_HOLD, Lifecycle.UNAVAILABLE},
    Lifecycle.ACQUIRED: {Lifecycle.EXTRACTED, Lifecycle.EXTRACTION_FAILED, Lifecycle.NEEDS_REVIEW},
    Lifecycle.EXTRACTED: {Lifecycle.INDEXED, Lifecycle.INDEXING_FAILED, Lifecycle.CATALOGED},
    Lifecycle.INDEXED: {Lifecycle.CATALOGED},
    Lifecycle.EXTRACTION_FAILED: {Lifecycle.NEEDS_REVIEW},
    Lifecycle.INDEXING_FAILED: {Lifecycle.NEEDS_REVIEW},
}


def can_transition(old: str, new: str) -> bool:
    """Return false rather than throwing when either stored state is unknown."""
    try:
        return Lifecycle(new) in TRANSITIONS.get(Lifecycle(old), set())
    except ValueError:
        return False