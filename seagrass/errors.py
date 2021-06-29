# Basic errors that can be thrown while using Seagrass


class SeagrassError(Exception):
    """A generic error for the Seagrass library."""


class EventNotFoundError(SeagrassError):
    """Raised when we try to reference an auditing event that does not currently
    exist."""

    event_name: str

    def __init__(self, event_name: str) -> None:
        """Create a new EventNotFoundError.

        :param str event_name: the name of the event that could not be found.
        """
        self.event_name = event_name
        msg = f"Audit event not found: {event_name}"
        super().__init__(msg)
