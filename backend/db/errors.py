class StorageError(Exception):
    """Base class for storage-layer errors."""


class FeedNotFoundError(StorageError):
    """Raised when a feed-specific operation cannot find the feed."""


class ArticleNotFoundError(StorageError):
    """Raised when an article-specific operation cannot find the article."""


class DuplicateFeedUrlError(StorageError):
    """Raised when a feed URL conflicts with an existing feed."""
