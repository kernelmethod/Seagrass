# flake8: noqa: F401
import functools as _functools
import seagrass._typing as t
from .auditor import Auditor, get_audit_logger, DEFAULT_LOGGER_NAME
from .events import get_current_event
from . import base, errors, events, hooks
from contextvars import ContextVar as _ContextVar
from logging import Logger as _Logger

# "Global auditor" that can be used to audit events without having to create an
# auditor first.
_GLOBAL_AUDITOR: _ContextVar[Auditor] = _ContextVar(
    "_GLOBAL_SEAGRASS_AUDITOR", default=Auditor()
)


def global_auditor() -> Auditor:
    """Return the global Seagrass auditor."""
    return _GLOBAL_AUDITOR.get()


def auto(func: t.Callable) -> str:
    """Automatically generate an event name for a function being audited.

    **Examples:**

        .. testsetup:: auto-doctests

            from seagrass import Auditor
            from seagrass._docs import configure_logging
            configure_logging()
            auditor = Auditor()

        .. doctest:: auto-doctests

            >>> from seagrass import auto

            >>> from time import sleep

            >>> event = auditor.audit(auto, sleep)

            >>> event.__event_name__
            'time.sleep'

            >>> from pathlib import Path

            >>> event = auditor.audit(auto, Path.home)

            >>> event.__event_name__
            'pathlib.Path.home'
    """
    return f"{func.__module__}.{func.__qualname__}"


_F = t.TypeVar("_F", bound=t.Callable)

# Export parts of the external API of the global Auditor instance from the module
_EXPORTED_AUDITOR_ATTRIBUTES: t.List[str] = []


def _auditor_func(get_func: t.Callable[[], _F]) -> _F:
    """Wrap a function that retrieves a method of the global auditor so that it can be called as
    though it were the original method."""
    # Get the current global auditor's current instance of the input function
    # so that we can copy its name, annotations, documentation, etc.
    func = get_func()

    # Add the function's name to the _EXPORTED_AUDITOR_ATTRIBUTES list
    _EXPORTED_AUDITOR_ATTRIBUTES.append(func.__name__)

    @_functools.wraps(func)
    def wrapper(*args, **kwargs):
        return get_func()(*args, **kwargs)

    return t.cast(_F, wrapper)


audit = _auditor_func(lambda: global_auditor().audit)
async_audit = _auditor_func(lambda: global_auditor().audit)
create_event = _auditor_func(lambda: global_auditor().create_event)
raise_event = _auditor_func(lambda: global_auditor().raise_event)
toggle_event = _auditor_func(lambda: global_auditor().toggle_event)
toggle_auditing = _auditor_func(lambda: global_auditor().toggle_auditing)
start_auditing = _auditor_func(lambda: global_auditor().start_auditing)
add_hooks = _auditor_func(lambda: global_auditor().add_hooks)
reset_hooks = _auditor_func(lambda: global_auditor().reset_hooks)

# Remaining attributes are properties that need to be retrieved using the module __getattr__
# function
logger: _Logger

_EXPORTED_AUDITOR_ATTRIBUTES += ["logger"]


class create_global_auditor(t.ContextManager[Auditor]):
    """Create a context with a new global Auditor (as returned by the ``global_auditor()``
    function.) This is useful for when you want to import a module that uses Seagrass but
    don't want to add its events to the current global Auditor.

    If an Auditor is passed into this function, it will be used as the global auditor within the
    created context. Otherwise, a new Auditor instance will be created.

    :param Optional[Auditor] auditor: the :py:class:`seagrass.Auditor` instance that should be used
        as the global auditor. If no auditor is provided, a new one will be created.

    .. doctest:: create_global_auditor_doctests

        >>> import seagrass

        >>> from seagrass.hooks import LoggingHook

        >>> hook = LoggingHook(prehook_msg=lambda event, *args: f"called {event}")

        >>> with seagrass.create_global_auditor() as auditor:
        ...     @seagrass.audit("my_event", hooks=[hook])
        ...     def my_event():
        ...         pass

        >>> with seagrass.start_auditing():
        ...     my_event()

        >>> with auditor.start_auditing():
        ...     my_event()
        (DEBUG) seagrass: called my_event
    """

    def __init__(self, auditor: t.Optional[Auditor] = None) -> None:
        if auditor is None:
            self.new_auditor = Auditor()
        else:
            self.new_auditor = auditor

    def __enter__(self) -> Auditor:
        self.auditor_token = _GLOBAL_AUDITOR.set(self.new_auditor)
        return self.new_auditor

    def __exit__(self, *args) -> None:
        _GLOBAL_AUDITOR.reset(self.auditor_token)


__all__ = [
    "base",
    "errors",
    "events",
    "hooks",
    "DEFAULT_LOGGER_NAME",
    "Auditor",
    "get_audit_logger",
    "get_current_event",
    "global_auditor",
    "create_global_auditor",
    "auto",
]

__all__ += _EXPORTED_AUDITOR_ATTRIBUTES


def __getattr__(attr) -> t.Any:
    if attr == "logger":
        return global_auditor().logger
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {attr!r}")
