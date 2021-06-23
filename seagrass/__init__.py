# flake8: noqa: F401
import typing as t
from .auditor import Auditor, get_audit_logger, DEFAULT_LOGGER_NAME
from contextvars import ContextVar

# "Global auditor" that can be used to audit events without having to create an
# auditor first.
_GLOBAL_AUDITOR: ContextVar[Auditor] = ContextVar(
    "_GLOBAL_SEAGRASS_AUDITOR", default=Auditor()
)


def global_auditor() -> Auditor:
    """Return the global Seagrass auditor."""
    return _GLOBAL_AUDITOR.get()


# Export parts of the external API of the global Auditor instance from the module
_EXPORTED_AUDITOR_ATTRIBUTES = [
    "audit",
    "create_event",
    "raise_event",
    "toggle_event",
    "toggle_auditing",
    "start_auditing",
    "add_hooks",
    "reset_hooks",
    "log_results",
    "logger",
]


def _global_auditor_attrs():
    # Collect the exported attributes of the current global auditor into a dictionary
    auditor = global_auditor()
    return dict((attr, getattr(auditor, attr)) for attr in _EXPORTED_AUDITOR_ATTRIBUTES)


# Create context variables to cache attributes that we've already looked up on the auditor. This makes
# lookups on module attributes a bit faster.
_GLOBAL_AUDITOR_ATTRS: ContextVar[t.Dict[str, t.Any]] = ContextVar(
    "_GLOBAL_AUDITOR_ATTRS", default=_global_auditor_attrs()
)


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
        self.attrs_token = _GLOBAL_AUDITOR_ATTRS.set(_global_auditor_attrs())
        return self.new_auditor

    def __exit__(self, *args) -> None:
        _GLOBAL_AUDITOR.reset(self.auditor_token)
        _GLOBAL_AUDITOR_ATTRS.reset(self.attrs_token)


__all__ = [
    "Auditor",
    "get_audit_logger",
    "global_auditor",
    "create_global_auditor",
]

__all__ += _EXPORTED_AUDITOR_ATTRIBUTES


def __getattr__(attr: str) -> t.Any:
    if (auditor_attr := _GLOBAL_AUDITOR_ATTRS.get(attr)) is not None:
        return auditor_attr
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {attr!r}")


def __dir__() -> t.List[str]:
    return __all__
