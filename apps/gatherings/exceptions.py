from __future__ import annotations


class GatheringError(Exception):
    """Base domain error for gatherings."""


class GatheringNotFound(GatheringError):
    pass


class GatheringCancelled(GatheringError):
    pass


class GatheringAtCapacity(GatheringError):
    pass


class GatheringAlreadyJoined(GatheringError):
    pass


class GatheringCommunityRequired(GatheringError):
    pass


class GatheringEligibilityError(GatheringError):
    pass


class GatheringIdentityRequired(GatheringError):
    """Raised when join/create requires Didit identity verification."""


class GatheringCoverError(GatheringError):
    pass


class GatheringEditForbidden(GatheringError):
    pass


class GatheringCreatorCannotJoin(GatheringError):
    """Creators host the gathering and do not occupy an attendee seat."""


class GatheringDeletionPending(GatheringError):
    pass


class GatheringDeletionNotPending(GatheringError):
    pass
