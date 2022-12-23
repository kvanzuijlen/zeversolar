class ZeverSolarError(Exception):
    """
    Base of all exceptions thrown by this package
    """


class ZeverSolarTimeout(ZeverSolarError):
    """
    Exception thrown when a timeout occurs
    """


class ZeverSolarHTTPError(ZeverSolarError):
    """
    Exception thrown when an HTTP error occurs
    """


class ZeverSolarHTTPNotFound(ZeverSolarHTTPError):
    """
    Exception thrown when an HTTP Not Found (404) error occurs
    """
