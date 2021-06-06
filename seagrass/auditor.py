import functools
import logging
import typing as t
from contextlib import contextmanager
from seagrass.base import LoggableHook, ProtoHook
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
    hooks: t.Set[ProtoHook]
    __enabled: bool = False

    def __init__(self, logger: t.Union[str, logging.Logger] = "seagrass"):
        """Create a new Auditor instance."""
        if isinstance(logger, logging.Logger):
            self.logger = logger
        else:
            self.logger = logging.getLogger("seagrass")

        self.events = dict()
        self.event_wrappers = dict()
        self.hooks = set()

    def toggle_auditing(self, mode: bool):
        """Enable or disable auditing."""
        self.__enabled = mode

    @property
    def is_enabled(self):
        return self.__enabled

    @contextmanager
    def audit(self):
        """Create a new context within which the auditor is enabled."""
        try:
            self.toggle_auditing(True)
            _audit_logger_stack.append(self.logger)
            yield None
        finally:
            self.toggle_auditing(False)
            _audit_logger_stack.pop()

    def wrap(
        self,
        func: t.Callable,
        label: str,
        hooks: t.Optional[t.List[ProtoHook]] = None,
        **kwargs,
    ) -> t.Callable:
        """Wrap a function with a new auditing event."""

        if label in self.events:
            raise ValueError(
                f"An event with the label {label!r} has already been defined"
            )

        hooks = [] if hooks is None else hooks

        # Add hooks to the Auditor's `hooks` set
        for hook in hooks:
            self.hooks.add(hook)

        new_event = Event(func, label, hooks=hooks, **kwargs)
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

    def toggle_event(self, label: str, enabled: bool) -> None:
        """Toggle whether or not an event is enabled."""
        self.events[label].enabled = enabled

    def log_results(self):
        """Log results stored by hooks by calling `log_results` on all LoggableHooks."""
        for hook in self.hooks:
            if isinstance(hook, LoggableHook):
                hook.log_results(self.logger)
