import sys
import seagrass._typing as t
from contextvars import ContextVar, Token
from seagrass.base import CleanupHook
from types import FrameType

# Global variables that keep track of whether or not a TracingHook already exists.
_tracing_hook_exists: ContextVar[bool] = ContextVar(
    "_tracing_hook_exists", default=False
)
_tracing_hook: ContextVar[t.Optional["TracingHook.TraceFunc"]] = ContextVar(
    "_tracing_hook", default=None
)

TracingHookContext = t.Tuple[t.Optional[str], Token, Token]


class TracingHook(CleanupHook[TracingHookContext]):
    """Seagrass hook wrapper for tracing functions.

    **Example:** the code snippet below defines a new hook from
    :py:class:`~seagrass.hooks.TracingHook` that checks each frame to see if ``MY_VAR`` is defined
    locally, and if it is, it records ``MY_VAR``'s value.

    .. testsetup:: tracing-hook-example

        from seagrass._docs import configure_logging
        configure_logging()

    .. doctest:: tracing-hook-example

        >>> import seagrass

        >>> from seagrass.hooks import TracingHook

        >>> def tracefunc(frame, event, arg):
        ...     if "MY_VAR" in frame.f_locals:
        ...         MY_VAR = frame.f_locals["MY_VAR"]
        ...         logger = seagrass.get_audit_logger(None)
        ...         if logger is not None:
        ...             logger.info(f"Found MY_VAR={MY_VAR!r}")
        ...     return tracefunc

        >>> hook = TracingHook(tracefunc)

        >>> @seagrass.audit(seagrass.auto, hooks=[hook])
        ... def example():
        ...     MY_VAR = 100
        ...     MY_VAR = "hello, world!"

        >>> with seagrass.start_auditing():
        ...     example()
        (INFO) seagrass: Found MY_VAR=100
        (INFO) seagrass: Found MY_VAR='hello, world!'
    """

    class TraceFunc(t.Protocol):
        """A tracing function set by ``sys.settrace`` or ``threading.settrace``. The arguments to this
        function are the same as those to the function accepted by ``sys.settrace``."""

        def __call__(
            self, frame: FrameType, event: str, arg: t.Any
        ) -> t.Optional["TracingHook.TraceFunc"]:
            ...  # pragma: no cover

    def __init__(self, tracefunc: TraceFunc) -> None:
        """Create a new TracingHook.

        :param TraceFunc tracefunc: the function that should be used to perform tracing via
            `sys.settrace`_.

        .. _sys.settrace: https://docs.python.org/3/library/sys.html#sys.settrace
        """
        self.tracefunc = tracefunc

    # High prehook/posthook priority since we generally don't want to trace other
    # Seagrass hooks
    priority: int = 15

    __current_event: t.Optional[str] = None
    __is_active: bool = False

    @property
    def is_active(self) -> bool:
        """Return whether or not the hook is currently active (i.e., whether a Seagrass event that
        uses the hook is currently executing.)"""
        return self.__is_active

    @property
    def current_event(self) -> t.Optional[str]:
        """Return the current Seagrass event that is being executed."""
        return self.__current_event

    @staticmethod
    def get_current_tracing_hook():
        """Get the current global tracing hook."""
        return _tracing_hook.get()

    def __create_tracefunc(
        self,
        func: t.Optional["TraceFunc"],
    ) -> "TraceFunc":
        """A wrapper around the tracefunc function. This is the function that actually gets added
        with sys.settrace."""

        def tracefunc(
            frame: FrameType, event: str, arg: t.Any
        ) -> "TracingHook.TraceFunc":
            if func is not None and self.is_active:
                return self.__create_tracefunc(func(frame, event, arg))
            else:
                return self.__create_tracefunc(None)

        return tracefunc

    def prehook(
        self, event_name: str, args: t.Tuple[t.Any, ...], kwargs: t.Dict[str, t.Any]
    ) -> TracingHookContext:

        # Check whether another TracingHook is already active
        exists_token = _tracing_hook_exists.set(True)
        if exists_token.old_value != Token.MISSING and not self.is_active:
            _tracing_hook_exists.reset(exists_token)
            current_hook = _tracing_hook.get()
            raise ValueError(
                f"Only one TracingHook can be active at a time (current tracing hook = {current_hook!r})"
            )

        tracefunc_token = _tracing_hook.set(self.__create_tracefunc(self.tracefunc))
        old_event = self.__current_event
        self.__current_event = event_name
        self.__is_active = True

        sys.settrace(_tracing_hook.get())

        return old_event, exists_token, tracefunc_token

    def cleanup(
        self,
        event_name: str,
        context: TracingHookContext,
        exc: t.Tuple[t.Any, ...],
    ) -> None:
        old_event, exists_token, tracefunc_token = context

        self.__current_event = old_event
        self.__is_active = self.current_event is not None
        _tracing_hook_exists.reset(exists_token)
        _tracing_hook.reset(tracefunc_token)

        sys.settrace(_tracing_hook.get())
