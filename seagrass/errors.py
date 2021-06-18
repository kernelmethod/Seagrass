# Basic errors that can be thrown while using Seagrass

import os
import typing as t


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


class PosthookError(SeagrassError):
    """Raised when one or more Seagrass posthooks raised an error."""

    errors: t.List[Exception]

    def __init__(self, errors: t.List[Exception]) -> None:
        """Create a new PosthookError.

        :param List[Exception] errors: a list of errors that were raised.
        """
        self.errors = errors
        msg = f"{len(errors)} errors raised while processing posthooks and clean-up stages."
        msg += os.linesep
        msg += os.linesep.join(f"{e.__class__.__name__}: {e}" for e in errors)
        super().__init__(msg)
