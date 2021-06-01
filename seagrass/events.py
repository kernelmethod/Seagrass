import sys
from seagrass.hooks import ProtoHook
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
        "name",
        "raise_audit_event",
        "hooks",
        "prehook_audit_event_name",
        "posthook_audit_event_name",
    ]

    func: EventFnProtocol
    name: str
    raise_audit_event: bool
    hooks: List[ProtoHook]
    prehook_audit_event_name: str
    posthook_audit_event_name: str

    def __init__(
        self,
        func: Callable,
        name: str,
        hooks: List[ProtoHook] = [],
        raise_audit_event: bool = False,
        prehook_audit_event_name: Optional[str] = None,
        posthook_audit_event_name: Optional[str] = None,
    ):
        self.func = func
        self.name = name
        self.raise_audit_event = raise_audit_event
        self.hooks = hooks

        if prehook_audit_event_name is None:
            prehook_audit_event_name = f"prehook:{name}"
        if posthook_audit_event_name is None:
            posthook_audit_event_name = f"posthook:{name}"

        self.prehook_audit_event_name = prehook_audit_event_name
        self.posthook_audit_event_name = posthook_audit_event_name

    def __call__(self, *args, **kwargs):
        if self.raise_audit_event:
            sys.audit(self.prehook_audit_event_name, args, kwargs)

        # TODO (kernelmethod): execute hooks by priority levels
        for hook in self.hooks:
            hook.run_prehook(self.event_name, args, kwargs)

        result = self.func(*args, **kwargs)

        for hook in self.hooks:
            hook.run_posthook(self.event_name, result)

        if self.raise_audit_event:
            sys.audit(self.posthook_audit_event_name, result)

        return result
