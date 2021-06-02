import sys
from seagrass.base import ProtoHook
from typing import Any, Callable, List, Optional, Protocol


class EventFnProtocol(Protocol):
    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        pass


class Event:
    """A wrapped function that is under audit."""

    # Use __slots__ since feasibly users may want to create a large
    # number of events
    __slots__ = [
        "func",
        "enabled",
        "name",
        "raise_audit_event",
        "hooks",
        "prehook_audit_event_name",
        "posthook_audit_event_name",
        "__prehook_execution_order",
        "__posthook_execution_order",
    ]

    func: EventFnProtocol
    enabled: bool
    name: str
    raise_audit_event: bool
    hooks: List[ProtoHook]
    prehook_audit_event_name: str
    posthook_audit_event_name: str
    __prehook_execution_order: List[int]
    __posthook_execution_order: List[int]

    def __init__(
        self,
        func: Callable,
        name: str,
        enabled: bool = True,
        hooks: List[ProtoHook] = [],
        raise_audit_event: bool = False,
        prehook_audit_event_name: Optional[str] = None,
        posthook_audit_event_name: Optional[str] = None,
    ):
        self.func = func
        self.enabled = enabled
        self.name = name
        self.raise_audit_event = raise_audit_event
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
            range(len(hooks)), key=lambda i: (hooks[i].prehook_priority, i)
        )
        self.__posthook_execution_order = sorted(
            range(len(hooks)), key=lambda i: (-hooks[i].posthook_priority, -i)
        )

    def __call__(self, *args, **kwargs):
        if not self.enabled:
            # We just return the result of the wrapped function
            return self.func(*args, **kwargs)

        if self.raise_audit_event:
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

        if self.raise_audit_event:
            sys.audit(self.posthook_audit_event_name, result)

        return result
