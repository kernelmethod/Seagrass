import seagrass._typing as t
from contextvars import ContextVar
from dataclasses import dataclass
from seagrass.base import ProtoHook, CleanupHook
from types import TracebackType

T = t.TypeVar("T")

# Context variable used to store the current event
current_event: ContextVar[str] = ContextVar("seagrass_current_event")


@t.overload
def get_current_event() -> str:
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


@dataclass
class EventData:
    """A class that holds data corresponding to the event being executed."""

    event_name: str
    args: t.Tuple[t.Any, ...]
    kwargs: t.Dict[str, t.Any]
    result: t.Maybe[t.Any] = t.MISSING


class HookExecutionContext(t.Generic[T]):
    """A context manager that wraps around a hook that is in charge of its prehook and posthook."""

    __slots__: t.List[str] = ["data", "hook", "prehook_context"]

    def __init__(self, hook: ProtoHook[T], data: EventData) -> None:
        self.data = data
        self.hook = hook

    def __enter__(self) -> "HookExecutionContext":
        self.prehook_context: T = self.hook.prehook(
            self.data.event_name, self.data.args, self.data.kwargs
        )
        return self

    def __exit__(
        self,
        exc_type: t.Optional[t.Type[BaseException]],
        exc_val: t.Optional[BaseException],
        tb: t.Optional[TracebackType],
    ) -> None:
        try:
            if not isinstance(self.data.result, t.Missing):
                self.hook.posthook(
                    self.data.event_name, self.data.result, self.prehook_context
                )
        finally:
            if isinstance(self.hook, CleanupHook):
                exc = (exc_type, exc_val, tb)
                self.hook.cleanup(self.data.event_name, self.prehook_context, exc)

    async def __aenter__(self) -> "HookExecutionContext":
        return self.__enter__()

    async def __aexit__(
        self,
        exc_type: t.Optional[t.Type[BaseException]],
        exc_val: t.Optional[BaseException],
        tb: t.Optional[TracebackType],
    ) -> None:
        return self.__exit__(exc_type, exc_val, tb)
