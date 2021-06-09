import sys
import typing as t
from seagrass.base import ProtoHook, prehook_priority, posthook_priority

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
        "__prehook_execution_order",
        "__posthook_execution_order",
    ]

    enabled: bool
    name: str
    raise_runtime_events: bool
    hooks: t.List[ProtoHook]
    prehook_audit_event_name: str
    posthook_audit_event_name: str
    __prehook_execution_order: t.List[int]
    __posthook_execution_order: t.List[int]

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
        self.raise_runtime_events = raise_runtime_events
        self.hooks = hooks

        if prehook_audit_event_name is None:
            prehook_audit_event_name = f"prehook:{name}"
        if posthook_audit_event_name is None:
            posthook_audit_event_name = f"posthook:{name}"

        self.prehook_audit_event_name = prehook_audit_event_name
        self.posthook_audit_event_name = posthook_audit_event_name

        # Set the order of execution for prehooks and posthooks.
        # - Prehooks are ordered by ascending priority, then ascending list position
        # - Posthooks are ordered by descending priority, then descending list position
        self.__prehook_execution_order = sorted(
            range(len(hooks)), key=lambda i: (prehook_priority(hooks[i]), i)
        )
        self.__posthook_execution_order = sorted(
            range(len(hooks)), key=lambda i: (-posthook_priority(hooks[i]), -i)
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

        if self.raise_runtime_events:
            sys.audit(self.prehook_audit_event_name, args, kwargs)

        prehook_contexts = {}
        for hook_num in self.__prehook_execution_order:
            hook = self.hooks[hook_num]
            context = hook.prehook(self.name, args, kwargs)
            prehook_contexts[hook_num] = context

        result = self.func(*args, **kwargs)

        for hook_num in self.__posthook_execution_order:
            hook = self.hooks[hook_num]
            hook.posthook(self.name, result, prehook_contexts[hook_num])

        if self.raise_runtime_events:
            sys.audit(self.posthook_audit_event_name, result)

        return result
