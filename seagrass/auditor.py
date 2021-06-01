import functools
import logging
from contextlib import contextmanager
from seagrass.events import Event
from typing import Callable, Dict, Union


class Auditor:
    """
    An auditing instance that allows you to dynamically audit and profile
    code.
    """

    logger: logging.Logger
    events: Dict[str, Event] = {}
    event_wrappers: Dict[str, Callable] = {}
    __enabled: bool = False

    def __init__(self, logger: Union[str, logging.Logger] = "seagrass"):
        """Create a new Auditor instance."""
        if isinstance(logger, logging.Logger):
            self.logger = logger
        else:
            self.logger = logging.getLogger("seagrass")

    def enable(self, mode: bool):
        """Enable or disable auditing."""
        self.__enabled = mode

    @property
    def is_enabled(self):
        return self.__enabled

    @contextmanager
    def audit(self):
        """Create a new context within which the auditor is enabled."""
        try:
            self.enable(True)
            yield None
        finally:
            self.enable(False)

    def wrap(
        self,
        func: Callable,
        label: str,
        **kwargs,
    ) -> Callable:
        """Wrap a function to be audited."""

        if label in self.events:
            raise ValueError(
                f"An event with the label {label!r} has already been defined"
            )

        new_event = Event(func, label, **kwargs)
        self.events[label] = new_event

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not self.is_enabled:
                return new_event.func(*args, **kwargs)
            else:
                return new_event(*args, **kwargs)

        return wrapper

    def unwrap(self, label: str):
        """Stop auditing the event with the given label."""
