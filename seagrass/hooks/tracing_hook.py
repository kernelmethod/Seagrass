import sys
import typing as t
from abc import ABCMeta, abstractmethod
from contextvars import ContextVar, Token
from seagrass.base import CleanupHook
from types import FrameType

# Global variables that keep track of whether or not a TracingHook already exists.
_tracing_hook_exists: ContextVar[bool] = ContextVar(
    "_tracing_hook_exists", default=False
)
_tracing_hook: ContextVar["TracingHook"] = ContextVar("_tracing_hook")


class TracingHook(CleanupHook[t.Optional[str]], metaclass=ABCMeta):
    """Abstract base class for hooks that should be set as tracing functions.

    **Example:** the code snippet below defines a new hook from
    :py:class:`~seagrass.hooks.TracingHook` that checks each frame to see if ``MY_VAR`` is defined
    locally, and if it is, it records ``MY_VAR``'s value.

    .. testsetup:: tracing-hook-example

        from seagrass._docs import configure_logging
        configure_logging()

    .. doctest:: tracing-hook-example

        >>> import seagrass

        >>> from seagrass.hooks import TracingHook

        >>> class MyVarHook(TracingHook):
        ...     def tracefunc(self, frame, event, arg):
        ...         if "MY_VAR" in frame.f_locals:
        ...             MY_VAR = frame.f_locals["MY_VAR"]
        ...             if (logger := seagrass.get_audit_logger()) is not None:
        ...                 logger.info(f"Found {MY_VAR=!r}")
        ...         return self.tracefunc

        >>> hook = MyVarHook()

        >>> @seagrass.audit(seagrass.auto, hooks=[hook])
        ... def example():
        ...     MY_VAR = 100
        ...     MY_VAR = "hello, world!"

        >>> with hook:
        ...     with seagrass.start_auditing():
        ...         example()
        (INFO) seagrass: Found MY_VAR=100
        (INFO) seagrass: Found MY_VAR='hello, world!'
    """

    class TraceFunc(t.Protocol):
        """A tracing function set by ``sys.settrace`` or ``threading.settrace``. The arguments to this
        function are the same as those to the function accepted by ``sys.settrace``."""

        def __call__(
            self, frame: FrameType, event: str, arg: t.Any
        ) -> t.Optional["TracingHook.TraceFunc"]:
            ...

    @abstractmethod
    def tracefunc(
        self, frame: FrameType, event: str, arg: t.Any
    ) -> t.Optional[TraceFunc]:
        ...

    # High prehook/posthook priority since we generally don't want to trace other
    # Seagrass hooks
    prehook_priority: int = 15
    posthook_priority: int = 15

    __current_event: t.Optional[str] = None
    __is_active: bool = False
    __is_current_hook_token: t.Optional[Token[bool]] = None
    __old_hook_token: t.Optional[Token["TracingHook"]] = None

    @property
    def is_active(self) -> bool:
        """Return whether or not the hook is currently active (i.e., whether a Seagrass event that
        uses the hook is currently executing.)"""
        return self.__is_active

    @property
    def current_event(self) -> t.Optional[str]:
        """Return the current Seagrass event that is being executed."""
        return self.__current_event

    @property
    def is_current_tracing_hook(self) -> bool:
        """Returns True if this hook is the current global TracingHook."""
        if self.__is_current_hook_token is None:
            return False
        else:
            return t.cast(bool, self.__is_current_hook_token.old_value)

    @staticmethod
    def get_current_tracing_hook():
        """Get the current global tracing hook."""
        return _tracing_hook.get()

    def __enter__(self) -> "TracingHook":
        """Make the hook the current tracing hook. Only one TracingHook can be active at a time."""
        self.set_trace()
        return self

    def __exit__(self, *args) -> None:
        self.remove_trace()

    def __del__(self) -> None:
        self.remove_trace()

    def set_trace(self) -> None:
        """Make this hook the current tracing hook."""

        if self.__is_current_hook_token is not None:
            return

        if _tracing_hook_exists.get():
            raise ValueError("Only one TracingHook can exist at a time")

        self.__is_current_hook_token = _tracing_hook_exists.set(True)
        self.__old_hook_token = _tracing_hook.set(self)
        sys.settrace(self.__tracefunc)

    def remove_trace(self) -> None:
        """Stop using this hook as the current tracing hook."""

        if self.__is_current_hook_token is not None:
            _tracing_hook_exists.reset(self.__is_current_hook_token)

        if self.__old_hook_token is not None:
            _tracing_hook.reset(self.__old_hook_token)

        if self.is_current_tracing_hook:
            sys.settrace(None)

        self.__is_current_hook_token = None
        self.__old_hook_token = None

    def __tracefunc(
        self, frame: FrameType, event: str, arg: t.Any
    ) -> t.Optional["TraceFunc"]:
        """A wrapper around the tracefunc function. This is the function that actually gets added
        with sys.settrace."""
        if self.is_active:
            return self.tracefunc(frame, event, arg)
        else:
            return self.__tracefunc

    def prehook(
        self, event_name: str, args: t.Tuple[t.Any, ...], kwargs: t.Dict[str, t.Any]
    ) -> t.Optional[str]:
        old_event = self.__current_event
        self.__current_event = event_name
        self.__is_active = True
        return old_event

    def cleanup(
        self, event_name: str, context: t.Optional[str], exc: t.Optional[Exception]
    ) -> None:
        self.__current_event = context
        self.__is_active = self.current_event is not None


TracingHook.tracefunc.__doc__ = TracingHook.TraceFunc.__doc__
