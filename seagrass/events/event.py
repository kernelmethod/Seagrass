import sys
import seagrass._typing as t
from contextlib import ExitStack
from contextvars import ContextVar
from seagrass.base import ProtoHook

from .contexts import EventData, HookExecutionContext

# Context variable used to store the current event
current_event: ContextVar[str] = ContextVar("seagrass_current_event")

T = t.TypeVar("T")


@t.overload
def get_current_event(default: t.Missing) -> str:
    ...  # pragma: no cover


@t.overload
def get_current_event(default: T) -> t.Union[str, T]:
    ...  # pragma: no cover


def get_current_event(default: t.Maybe[T] = t.MISSING) -> t.Union[str, T]:
    """Get the current Seagrass event that is being executed.

    :raises LookupError: if no Seagrass event is currently under execution.
    """
    if isinstance(default, t.Missing):
        return current_event.get()
    else:
        return current_event.get(default)


# A type variable used to represent the function wrapped by an Event.
F = t.Callable[..., t.Any]


class Event:
    """Defines an event that is under audit. The event wraps around a function; instead of calling
    the function, we call the event, which first triggers any prehooks, *then* calls the function,
    and then triggers posthooks."""

    # Use __slots__ since feasibly users may want to create a large
    # number of events
    __slots__ = [
        "func",
        "enabled",
        "name",
        "raise_runtime_events",
        "hooks",
        "prehook_audit_event_name",
        "posthook_audit_event_name",
        "__hook_execution_order",
    ]

    enabled: bool
    name: str
    raise_runtime_events: bool
    hooks: t.List[ProtoHook]
    prehook_audit_event_name: str
    posthook_audit_event_name: str
    __hook_execution_order: t.List[int]

    def __init__(
        self,
        func: F,
        name: str,
        enabled: bool = True,
        hooks: t.List[ProtoHook] = [],
        raise_runtime_events: bool = False,
        prehook_audit_event_name: t.Optional[str] = None,
        posthook_audit_event_name: t.Optional[str] = None,
    ) -> None:
        """Create a new Event.

        :param Callable[[...],Any] func: the function being wrapped by this event.
        :param str name: the name of the event.
        :param bool enabled: whether to enable the event.
        :param List[ProtoHook] hooks: a list of all of the hooks that should be called whenever
            the event is triggered.
        :param bool raise_runtime_events: if ``True``, two `Python runtime audit events`_ are raised
            using `sys.audit`_ before and after running the function wrapped by the event.

            .. note::
                This parameter is only supported for Python version >= 3.8.

        :param Optional[str] prehook_audit_event_name: the name of the runtime audit event
            that should be raised *before* calling the wrapped function. If set to ``None``,
            the audit event is automatically named ``f"prehook:{name}"``. This parameter is
            ignored if ``raise_runtime_events`` is ``False``.
        :param Optional[str] posthook_audit_event_name: the name of the runtime audit event
            that should be raised *after* calling the wrapped function. If set to ``None``,
            the audit event is automatically named ``f"posthook:{name}"``. This parameter is
            ignored if ``raise_runtime_events`` is ``False``.

        .. _Python runtime audit events: https://www.python.org/dev/peps/pep-0578/
        .. _sys.audit: https://docs.python.org/3/library/sys.html#sys.audit
        """
        self.func: F = func
        self.enabled = enabled
        self.name = name
        self.hooks = []

        if raise_runtime_events:
            # Check that the Python version supports audit hooks
            if not hasattr(sys, "audit"):
                raise NotImplementedError(
                    "Runtime audit events are not supported for Python versions that don't "
                    "include sys.audit and sys.addaudithook"
                )

        self.raise_runtime_events = raise_runtime_events

        if prehook_audit_event_name is None:
            prehook_audit_event_name = f"prehook:{name}"
        if posthook_audit_event_name is None:
            posthook_audit_event_name = f"posthook:{name}"

        self.prehook_audit_event_name = prehook_audit_event_name
        self.posthook_audit_event_name = posthook_audit_event_name

        self.add_hooks(*hooks)

        # Set the order of execution for prehooks and posthooks.

    def add_hooks(self, *hooks: ProtoHook) -> None:
        """Add new hooks to the event.

        :param ProtoHook hooks: the hooks to add to the event.
        """
        for hook in hooks:
            self.hooks.append(hook)

        # Since we've updated the list of hooks, we need to re-determine the order
        # in which the hooks should be executed.
        self._set_hook_execution_order()

    def _set_hook_execution_order(self) -> None:
        """Determine the order in which the events' hooks should be executed."""
        # - Prehooks are ordered by ascending priority, then ascending list position
        # - Posthooks are ordered by descending priority, then descending list position
        self.__hook_execution_order = sorted(
            range(len(self.hooks)), key=lambda i: (self.hooks[i].priority, i)
        )

    def __call__(self, *args, **kwargs) -> t.Any:
        """Call the function wrapped by the Event. If the event is enabled, its prehooks and
        posthooks are executed before and after the execution of the wrapped function.

        :param args: the arguments to pass to the wrapped function.
        :param kwargs: the keyword arguments to pass to the wrapped function.
        """
        if not self.enabled:
            # We just return the result of the wrapped function
            return self.func(*args, **kwargs)

        token = current_event.set(self.name)

        if self.raise_runtime_events:
            sys.audit(self.prehook_audit_event_name, args, kwargs)

        event_data = EventData(self.name, args, kwargs)

        try:
            with ExitStack() as stack:
                for hook_num in self.__hook_execution_order:
                    hook = self.hooks[hook_num]
                    if hook.enabled:
                        stack.enter_context(HookExecutionContext(hook, event_data))

                event_data.result = self.func(*args, **kwargs)

            if event_data.result == t.MISSING:
                # This point should never be reached
                raise ValueError("Event result was not recorded")  # pragma: no cover

            if self.raise_runtime_events:
                sys.audit(self.posthook_audit_event_name, event_data.result)
        finally:
            current_event.reset(token)

        return event_data.result
