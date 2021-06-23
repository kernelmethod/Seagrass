# flake8: noqa: F401
import typing as t
from .auditor import Auditor, get_audit_logger, DEFAULT_LOGGER_NAME
from contextvars import ContextVar

# "Global auditor" that can be used to audit events without having to create an
# auditor first.
_GLOBAL_AUDITOR: ContextVar[Auditor] = ContextVar(
    "__GLOBAL_SEAGRASS_AUDITOR", default=Auditor()
)


def global_auditor() -> Auditor:
    """Return the global Seagrass auditor."""
    return _GLOBAL_AUDITOR.get()


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
        self.token = _GLOBAL_AUDITOR.set(self.new_auditor)
        return self.new_auditor

    def __exit__(self, *args) -> None:
        _GLOBAL_AUDITOR.reset(self.token)


# Export the external API of the global Auditor instance from the module
__EXPORTED_AUDITOR_FUNCTIONS = set(
    [
        "audit",
        "create_event",
        "raise_event",
        "toggle_event",
        "toggle_auditing",
        "start_auditing",
        "add_hooks",
        "reset_hooks",
        "log_results",
    ]
)


def __getattr__(attr: str) -> t.Any:
    if attr in __EXPORTED_AUDITOR_FUNCTIONS:
        return getattr(global_auditor(), attr)
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {attr!r}")


__all__ = [
    "Auditor",
    "get_audit_logger",
    "global_auditor",
]

__all__ += list(__EXPORTED_AUDITOR_FUNCTIONS)
