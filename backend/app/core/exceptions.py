class ProcessingError(Exception):
    """Base exception for processing errors."""
    pass

class DocumentTooLargeError(ProcessingError):
    """Raised when a document exceeds the maximum allowed size."""
    pass

class UnsupportedFormatError(ProcessingError):
    """Raised when an unsupported document format is encountered."""
    pass

class ScrapingError(ProcessingError):
    """Raised when web scraping fails."""
    pass
