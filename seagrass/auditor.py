import functools
import logging
import typing as t
from contextlib import contextmanager
from seagrass.events import Event

# Global variable that keeps track of the auditor's logger for the
# current auditing context.
_audit_logger_stack: t.List[logging.Logger] = []


def get_audit_logger() -> t.Optional[logging.Logger]:
    if len(_audit_logger_stack) == 0:
        return None
    else:
        return _audit_logger_stack[-1]


class Auditor:
    """
    An auditing instance that allows you to dynamically audit and profile
    code.
    """

    logger: logging.Logger
    events: t.Dict[str, Event]
    event_wrappers: t.Dict[str, t.Callable]
    __enabled: bool = False

    def __init__(self, logger: t.Union[str, logging.Logger] = "seagrass"):
        """Create a new Auditor instance."""
        if isinstance(logger, logging.Logger):
            self.logger = logger
        else:
            self.logger = logging.getLogger("seagrass")

        self.events = dict()
        self.event_wrappers = dict()

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
            _audit_logger_stack.append(self.logger)
            yield None
        finally:
            self.enable(False)
            _audit_logger_stack.pop()

    def wrap(
        self,
        func: t.Callable,
        label: str,
        **kwargs,
    ) -> t.Callable:
        """Wrap a function with a new auditing event."""

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

    def decorate(
        self,
        label: str,
        **kwargs,
    ) -> t.Callable:
        """A function decorator that tells the auditor to monitor the decorated function."""

        def wrapper(func):
            return self.wrap(func, label, **kwargs)

        return wrapper

    def unwrap(self, label: str):
        """Stop auditing the event with the given label."""
