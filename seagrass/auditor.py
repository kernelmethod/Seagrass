import functools
import logging
import typing as t
from contextlib import contextmanager
from seagrass.base import LogResultsHook, ProtoHook
from seagrass.errors import EventNotFoundError
from seagrass.events import Event

# Global variable that keeps track of the auditor's logger for the
# current auditing context.
_audit_logger_stack: t.List[logging.Logger] = []

# A type variable used to represent a function that can take
# arbitrary/unknown inputs and returns an arbitrary/unknown type
F = t.TypeVar("F", bound=t.Callable[..., t.Any])


def _empty_event_func(*args, **kwargs) -> None:
    """A function used to define empty events. This function can take an arbitrary combination
    of parameters, but internally it does nothing."""


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

    def __init__(self, logger: t.Union[str, logging.Logger] = "seagrass") -> None:
        """Create a new Auditor instance.

        :param Union[str,logging.Logger] logger: The logger that this auditor should use. When set
            to a string the auditor uses the logger returned by ``logging.getLogger(logger)``.
        """
        if isinstance(logger, logging.Logger):
            self.logger = logger
        else:
            self.logger = logging.getLogger(logger)

        self.events = dict()
        self.event_wrappers = dict()
        self.hooks = set()

    @property
    def is_enabled(self) -> bool:
        """Return whether or not the auditor is enabled.

        :type: bool
        """
        return self.__enabled

    def toggle_auditing(self, mode: bool) -> None:
        """Enable or disable auditing.

        :param bool mode: When set to ``True``, auditing is enabled; when set to ``False``,
            auditing is disabled.
        """
        self.__enabled = mode

    @contextmanager
    def audit(self) -> t.Iterator[None]:
        """Create a new context within which the auditor is enabled. You can replicate this
        functionality by calling :py:meth:`toggle_auditing`, e.g.

        .. testsetup::

            from seagrass import Auditor
            auditor = Auditor()

        .. testcode::

            try:
                auditor.toggle_auditing(True)
                # Put code under audit here
                ...
            finally:
                auditor.toggle_auditing(False)

        However, using ``with auditor.audit()`` in place of ``auditor.toggle_auditing`` has some
        additional benefits too, e.g. it allows you to access the logger for the most recent
        auditing context using ``seagrass.get_audit_logger``.
        """
        try:
            self.toggle_auditing(True)
            _audit_logger_stack.append(self.logger)
            yield None
        finally:
            self.toggle_auditing(False)
            _audit_logger_stack.pop()

    def wrap(
        self,
        func: F,
        event_name: str,
        hooks: t.Optional[t.List[ProtoHook]] = None,
        **kwargs,
    ) -> F:
        """Wrap a function with a new auditing event.

        :param Callable func: the function that should be wrapped in a new event.
        :param str event_name: the name of the new event. Event names must be unique.
        :param Optional[List[ProtoHook]] hooks: a list of hooks to call whenever the new event is
            triggered.
        :param kwargs: keyword arguments to pass on to ``Event.__init__``.

        **Example:** create an event over the function ``json.dumps`` using ``wrap``:

        .. testsetup::

            from seagrass import Auditor
            auditor = Auditor()

        .. doctest::

            >>> import json
            >>> from seagrass.hooks import CounterHook
            >>> hook = CounterHook()
            >>> audumps = auditor.wrap(json.dumps, "audit.json.dumps", hooks=[hook])
            >>> setattr(json, "dumps", audumps)
            >>> hook.event_counter["audit.json.dumps"]
            0
            >>> with auditor.audit():
            ...     json.dumps({"a": 1, "b": 2})
            '{"a": 1, "b": 2}'
            >>> hook.event_counter["audit.json.dumps"]
            1
        """

        if event_name in self.events:
            raise ValueError(
                f"An event with the name '{event_name}' has already been defined"
            )

        hooks = [] if hooks is None else hooks

        # Add hooks to the Auditor's `hooks` set
        for hook in hooks:
            self.hooks.add(hook)

        new_event = Event(func, event_name, hooks=hooks, **kwargs)
        self.events[event_name] = new_event

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not self.is_enabled:
                return new_event.func(*args, **kwargs)
            else:
                return new_event(*args, **kwargs)

        self.event_wrappers[event_name] = wrapper
        return t.cast(F, wrapper)

    def decorate(
        self,
        event_name: str,
        **kwargs,
    ) -> t.Callable[[F], F]:
        """A function decorator that tells the auditor to monitor the decorated function.

        .. testcode::

            from seagrass import Auditor
            from seagrass.hooks import CounterHook
            auditor = Auditor()

            @auditor.decorate("event.add", hooks=[CounterHook()])
            def add(x, y):
                return x + y
        """

        def wrapper(func: F):
            return self.wrap(func, event_name, **kwargs)

        return wrapper

    def create_event(self, event_name: str, **kwargs) -> t.Callable[..., None]:
        """Create a new "empty" event. When this event is executed, it runs any hooks that are
        associated with the event, but the function wrapped by the event itself does nothing.

        :param str event_name: the name of the event that should be created. Event names should
            be unique.
        :param kwargs: keyword arguments. The keyword arguments for this function are the same
            as those for :py:meth:`wrap`.
        :return: returns a wrapper function around the event that was created.

        **Example:**

        .. doctest::

            >>> from seagrass import Auditor

            >>> from seagrass.hooks import CounterHook

            >>> auditor = Auditor()

            >>> hook = CounterHook()

            >>> wrapper = auditor.create_event("my_signal", hooks=[hook])

            >>> hook.event_counter["my_signal"]
            0

            >>> with auditor.audit():
            ...     auditor.raise_event("my_signal")

            >>> hook.event_counter["my_signal"]
            1
        """
        return self.wrap(_empty_event_func, event_name, **kwargs)

    def raise_event(self, event_name: str, *args, **kwargs) -> t.Any:
        """Trigger an audit event using the input arguments and keyword arguments.

        :param str event_name: the name of the event to be raised.
        :param args: arguments to pass to the event.
        :param kwargs: keyword arguments to pass to the event.
        :return: returns the output of the event that was called.
        :rtype: Any
        :raises seagrass.errors.EventNotFoundError: if the auditor can't find the event with the
            provided name.
        """

        if (wrapper := self.event_wrappers.get(event_name)) is not None:
            return wrapper(*args, **kwargs)
        else:
            raise EventNotFoundError(event_name)

    def toggle_event(self, event_name: str, enabled: bool) -> None:
        """Enables or disables an auditing event.

        :param str event_name: the name of the event to toggle.
        :param bool enabled: whether to enable or disabled the event.

        **Example:**

        .. testsetup::

            from seagrass import Auditor
            auditor = Auditor()

        .. doctest::

            >>> from seagrass.hooks import CounterHook
            >>> hook = CounterHook()
            >>> @auditor.decorate("event.say_hello", hooks=[hook])
            ... def say_hello(name):
            ...     return f"Hello, {name}!"
            >>> hook.event_counter["event.say_hello"]
            0
            >>> with auditor.audit():
            ...     say_hello("Alice")
            'Hello, Alice!'
            >>> hook.event_counter["event.say_hello"]
            1
            >>> # Disable the "event.say_hello" event
            >>> auditor.toggle_event("event.say_hello", False)
            >>> with auditor.audit():
            ...     # Since event.say_hello is disabled, the following call to
            ...     # say_hello will not contribute to its event counter.
            ...     say_hello("Bob")
            'Hello, Bob!'
            >>> hook.event_counter["event.say_hello"]
            1

        """
        self.events[event_name].enabled = enabled

    def log_results(self) -> None:
        """Log results stored by hooks by calling `log_results` on all
        :py:class:`~seagrass.base.LogResultsHook` hooks."""
        for hook in self.hooks:
            if isinstance(hook, LogResultsHook):
                hook.log_results(self.logger)


def get_audit_logger() -> t.Optional[logging.Logger]:
    """Get the logger belonging to the auditor in the current auditing context. If this function
    is executed outside of an auditing context, it returns ``None``.

    This function only works in auditing contexts created by :py:meth:`Auditor.audit`; it will
    be unable to get the logger for the current auditing context if you use
    :py:meth:`Auditor.toggle_auditing`.

    :return: the logger for the most recent auditing context (or ``None``).
    :rtype: Optional[logging.Logger]
    """
    if len(_audit_logger_stack) == 0:
        return None
    else:
        return _audit_logger_stack[-1]
