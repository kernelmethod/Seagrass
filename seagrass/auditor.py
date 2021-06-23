import functools
import logging
import typing as t
from contextlib import contextmanager
from contextvars import ContextVar
from seagrass.base import LogResultsHook, ProtoHook, ResettableHook
from seagrass.errors import EventNotFoundError
from seagrass.events import Event

# The name of the default logger used by Seagrass
DEFAULT_LOGGER_NAME: str = "seagrass"

# A context variable that keeps track of the auditor's logger for the
# current auditing context.
_current_audit_logger: ContextVar[t.Optional[logging.Logger]] = ContextVar(
    "audit_logger", default=None
)

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

    def __init__(
        self, logger: t.Union[str, logging.Logger] = DEFAULT_LOGGER_NAME
    ) -> None:
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
        self.reset_filter()

    @property
    def enabled(self) -> bool:
        """Return whether or not the auditor is enabled.

        :type: bool
        """
        return self.__enabled

    @property
    def event_filter(self) -> t.Callable[[str], bool]:
        """A filter over the events being audited.

        :param EventFilter filter: the filter that should be added to the auditor. The filter
            should satisfy the :py:class:`seagrass.events.EventFilter` interface -- that is, they
            should be functions that take a single string and return a bool.
        :raises TypeError: if the filters don't satisfy the
            :py:class:`~seagrass.events.EventFilter` interface.

        **Examples:**

        .. testsetup:: filter-events-doctests

            from seagrass import Auditor
            from seagrass._docs import configure_logging
            configure_logging()
            auditor = Auditor()

        .. doctest:: filter-events-doctests

            >>> from seagrass.hooks import LoggingHook

            >>> hook = LoggingHook(prehook_msg = lambda event, *args: f"{event} called")

            >>> _ = auditor.create_event("example.foo", hooks=[hook])

            >>> with auditor.start_auditing():
            ...     auditor.raise_event("example.foo")
            (DEBUG) seagrass: example.foo called

            >>> auditor.event_filter = lambda event: not event.startswith("example.")

            >>> with auditor.start_auditing():
            ...     auditor.raise_event("example.foo")
        """
        return self.__event_filter

    @event_filter.setter
    def event_filter(self, filter: t.Callable[[str], bool]):
        self.__event_filter = filter

    def reset_filter(self) -> None:
        """Reset the event filter used by the Auditor."""
        self.event_filter = lambda event: True

    def toggle_auditing(self, mode: bool) -> None:
        """Enable or disable auditing.

        :param bool mode: When set to ``True``, auditing is enabled; when set to ``False``,
            auditing is disabled.
        """
        self.__enabled = mode

    @contextmanager
    def start_auditing(
        self,
        filter: t.Optional[t.Callable[[str], bool]] = None,
        reset_hooks: bool = False,
        log_results: bool = False,
    ) -> t.Iterator[None]:
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

        However, using ``with auditor.start_auditing()`` in place of ``auditor.toggle_auditing`` has
        some additional benefits too, e.g. it allows you to access the logger for the most recent
        auditing context using ``seagrass.get_audit_logger``.

        :param Callable[[str],bool] filter: a filter to apply on which events should be audited.
        :param bool log_results: Log hooks results with :py:meth:`log_results` before exiting
            the auditing context.
        :param bool reset_hooks: Reset hooks with :py:meth:`reset`: before exiting the
            auditing context.
        """
        try:
            logger_token = _current_audit_logger.set(self.logger)

            if filter is not None:
                old_filter = self.event_filter
                self.event_filter = filter

            self.toggle_auditing(True)
            yield None

        finally:
            self.toggle_auditing(False)
            _current_audit_logger.reset(logger_token)

            if filter is not None:
                self.event_filter = old_filter

            if log_results:
                self.log_results()
            if reset_hooks:
                self.reset_hooks()

    # Overload the audit function so that it can be called either as a decorator or as
    # a regular function.

    @t.overload
    def audit(
        self,
        event_name: str,
        **kwargs,
    ) -> t.Callable[[F], F]:
        ...  # pragma: no cover

    @t.overload
    def audit(
        self,
        event_name: str,
        func: F,
        hooks: t.Optional[t.List[ProtoHook]] = None,
        **kwargs,
    ) -> F:
        ...  # pragma: no cover

    def audit(
        self,
        event_name: str,
        func: t.Optional[F] = None,
        hooks: t.Optional[t.List[ProtoHook]] = None,
        **kwargs,
    ):
        """Wrap a function with a new auditing event. You can call ``audit`` either as a function
        decorator or as a regular method of :py:class:`Auditor`.

        :param Optional[Callable] func: the function that should be wrapped in a new event.
        :param str event_name: the name of the new event. Event names must be unique.
        :param Optional[List[ProtoHook]] hooks: a list of hooks to call whenever the new event is
            triggered.
        :param kwargs: keyword arguments to pass on to ``Event.__init__``.

        **Examples:** create an event over the function ``json.dumps`` using ``wrap``:

        .. testsetup::

            from seagrass import Auditor
            auditor = Auditor()

        .. doctest::

            >>> import json
            >>> from seagrass.hooks import CounterHook
            >>> hook = CounterHook()
            >>> audumps = auditor.audit("audit.json.dumps", json.dumps, hooks=[hook])
            >>> setattr(json, "dumps", audumps)
            >>> hook.event_counter["audit.json.dumps"]
            0
            >>> with auditor.start_auditing():
            ...     json.dumps({"a": 1, "b": 2})
            '{"a": 1, "b": 2}'
            >>> hook.event_counter["audit.json.dumps"]
            1

        Here is another example where we call ``auditor.audit`` as a decorator for a function
        ``add``:

        .. testcode::

            from seagrass import Auditor
            from seagrass.hooks import CounterHook
            auditor = Auditor()

            @auditor.audit("event.add", hooks=[CounterHook()])
            def add(x, y):
                return x + y

        """

        # If func is None, we assume that audit() was called as a function decorator, and
        # we return another decorator that can be called around the function.
        if func is None:

            def decorator(func: F):
                return self.audit(event_name, func, hooks=hooks, **kwargs)

            return decorator

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
            if not self.enabled or not self.event_filter(event_name):
                return new_event.func(*args, **kwargs)
            else:
                return new_event(*args, **kwargs)

        self.event_wrappers[event_name] = wrapper
        return t.cast(F, wrapper)

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

            >>> with auditor.start_auditing():
            ...     auditor.raise_event("my_signal")

            >>> hook.event_counter["my_signal"]
            1
        """
        return self.audit(event_name, _empty_event_func, **kwargs)

    def reset_hooks(self) -> None:
        """Reset all of the hooks used by this Auditor."""
        for hook in self.hooks:
            if isinstance(hook, ResettableHook):
                hook.reset()

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

    def add_hooks(self, event_name: str, *hooks: ProtoHook) -> None:
        """Add new hooks to an auditing event.

        :param str event_name: the name of the event to add the hooks to.
        :param ProtoHook hooks: the hooks that should be added to the event.
        :raises seagrass.errors.EventNotFoundError: if the auditor can't find the event with the
            provided name.
        """
        if (event := self.events.get(event_name)) is not None:
            event.add_hooks(*hooks)
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
            >>> @auditor.audit("event.say_hello", hooks=[hook])
            ... def say_hello(name):
            ...     return f"Hello, {name}!"
            >>> hook.event_counter["event.say_hello"]
            0
            >>> with auditor.start_auditing():
            ...     say_hello("Alice")
            'Hello, Alice!'
            >>> hook.event_counter["event.say_hello"]
            1
            >>> # Disable the "event.say_hello" event
            >>> auditor.toggle_event("event.say_hello", False)
            >>> with auditor.start_auditing():
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
    return _current_audit_logger.get()
