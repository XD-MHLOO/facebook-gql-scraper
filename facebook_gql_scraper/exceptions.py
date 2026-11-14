class FacebookGqlScraperException(Exception):
    """Base for all errors raised by this library."""


# Session / auth 
class SessionExpiredError(FacebookGqlScraperException):
    """Facebook invalidated the session (cookie expired or was revoked)."""


# Access 
class FacebookAccessException(FacebookGqlScraperException):
    """Facebook refused access to the requested resource."""


# Not found 
class FacebookNotFoundError(FacebookGqlScraperException):
    """The requested resource does not exist on Facebook."""


class ProfileNotFoundError(FacebookNotFoundError):
    """The profile was not found on Facebook."""


class PostNotFoundError(FacebookNotFoundError):
    """The post was not found on Facebook."""

class MediaPostNotFoundError(FacebookNotFoundError):
    """The media post was not found on Facebook."""
    
class GroupNotFoundError(FacebookNotFoundError):
    """The group was not found on Facebook."""


class MarketplaceListingNotFoundError(FacebookNotFoundError):
    """The Marketplace listing was not found on Facebook."""


# Resource not exposed 
class ResourceNotAvailableException(FacebookAccessException):
    """The resource exists but is not exposed by this profile/group."""


class FollowersNotAvailableException(ResourceNotAvailableException):
    """The profile does not expose its followers list."""


class FolloweesNotAvailableException(ResourceNotAvailableException):
    """The profile does not expose its following list."""


class FriendFollowersNotAvailableException(ResourceNotAvailableException):
    """The profile does not expose friends with follower relationships."""


class FriendFolloweesNotAvailableException(ResourceNotAvailableException):
    """The profile does not expose friends with following relationships."""


class PhotoNotAvailableException(ResourceNotAvailableException):
    """The profile does not expose its photos."""


class ReelsNotAvailableException(ResourceNotAvailableException):
    """The profile does not expose its reels."""


class DocIdStillInvalidError(FacebookGqlScraperException):
    """Facebook rejected the doc_id even after re-capturing."""


class DtsgTokenStillInvalidError(FacebookGqlScraperException):
    """Facebook rejected the fb_dtsg token even after re-capturing."""


class DtsgTokenFetchError(FacebookGqlScraperException):
    """Failed to obtain the fb_dtsg token from Facebook."""

class SchemaChangedError(FacebookGqlScraperException):
    """Facebook's GraphQL schema for an operation changed — variables no longer match."""

class EmptyNodeError(FacebookGqlScraperException):
    """Facebook return empty node response."""

# ---------- invalid usage ----------

class InvalidUsageError(FacebookGqlScraperException, ValueError):
    """The SDK was called incorrectly (bad value, missing required parent, …)."""


class InvalidIdTypeError(InvalidUsageError):
    """The provided id belongs to a different entity type than the one requested."""