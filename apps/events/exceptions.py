from __future__ import annotations


class EventError(Exception):
    """Base domain error for events."""


class EventNotFound(EventError):
    pass


class EventCancelled(EventError):
    pass


class EventAtCapacity(EventError):
    pass


class EventAlreadyJoined(EventError):
    pass


class JoinRequestNotFound(EventError):
    pass


class JoinRequestNotPending(EventError):
    pass


class EventCommunityRequired(EventError):
    pass


class EventEditForbidden(EventError):
    pass


class EventCoverError(EventError):
    pass


class EventIdentityRequired(EventError):
    """Raised when join requires Didit identity verification."""
