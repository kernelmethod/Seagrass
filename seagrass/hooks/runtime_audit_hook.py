import sys
import typing as t
from abc import ABCMeta, abstractmethod
from contextlib import contextmanager
from functools import wraps
from seagrass import get_audit_logger
from seagrass.base import ProtoHook

# Type variable used to represent value returned from a function
R = t.TypeVar("R")


class RuntimeAuditHook(ProtoHook[t.Optional[str]], metaclass=ABCMeta):
    """Abstract base class that serves as a template for hooks whose body should be run as Python
    runtime audit hooks, in accordance with `PEP 578`_.

    **Examples:** in the code below, ``RuntimeEventCounterHook`` is a class derived from the
    ``RuntimeAuditHook`` base class that prints every time a runtime audit event is triggered.

    .. testsetup:: runtime-audit-hook-example

        from seagrass.auditor import Auditor
        auditor = Auditor()

    .. doctest:: runtime-audit-hook-example

        >>> import sys

        >>> from seagrass.hooks import RuntimeAuditHook

        >>> class RuntimeEventCounterHook(RuntimeAuditHook):
        ...     def __init__(self):
        ...         super().__init__()
        ...
        ...     def sys_hook(self, event, args):
        ...         print(f"Encountered {event=!r} with {args=}")
        ...

        >>> hook = RuntimeEventCounterHook()

        >>> @auditor.audit("my_event", hooks=[hook])
        ... def my_event(*args):
        ...     sys.audit("sys.my_event", *args)

        >>> with auditor.start_auditing():
        ...     my_event(42, "hello, world")
        Encountered event='sys.my_event' with args=(42, 'hello, world')

    .. _PEP 578: https://www.python.org/dev/peps/pep-0578/
    """

    # Default value of the propagate_errors attribute
    PROPAGATE_ERRORS_DEFAULT: t.Final[bool] = True

    # Whether to propagate errors from sys_hook.
    propagate_errors: bool = PROPAGATE_ERRORS_DEFAULT

    __current_event: t.Optional[str] = None
    __is_active: bool

    @abstractmethod
    def sys_hook(self, event: str, args: t.Tuple[t.Any, ...]) -> None:
        """The runtime auditing hook that gets executed every time sys.audit() is called.
        This must be defined in child classes of RuntimeAuditHook."""

    @property
    def is_active(self) -> bool:
        """Return whether or not the hook is currently active (i.e., whether a Seagrass event that
        uses the hook is currently executing.)"""
        return self.__is_active

    @property
    def current_event(self) -> t.Optional[str]:
        """Returns the current Seagrass event being executed that's hooked by this function. If no
        events using this hook are being executed, ``current_event`` is ``None``."""
        return self.__current_event

    def __update_properties(self) -> None:
        self.__is_active = self.current_event is not None

    def __update(func: t.Callable[..., R]) -> t.Callable[..., R]:  # type: ignore[misc]
        # NOTE: mypy will flag this as erroneous because it is a non-static method that doesn't
        # include the argument 'self'
        # Ref: https://github.com/python/mypy/issues/7778
        """Function decorator that causes functions to reset the current_event and is_active
        properties every time it gets called."""

        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            finally:
                self.__update_properties()

        return wrapper

    def __init__(self, propagate_errors: t.Optional[bool] = None) -> None:
        if propagate_errors is not None:
            self.propagate_errors = propagate_errors
        self.__update_properties()

        # Add the runtime audit hook after initializing the properties since the hook will in most
        # cases use some of the properties of the RuntimeAuditHook.
        sys.addaudithook(self.__sys_hook)

    def __sys_hook(self, event: str, args: t.Tuple[t.Any, ...]) -> None:
        """A wrapper around the sys_hook abstract method that first checks whether the hook
        is currently active before it executes anything. This is the function that actually
        gets added with sys.addaudithook, not sys_hook."""
        if self.is_active:
            try:
                self.sys_hook(event, args)
            except Exception as ex:
                if self.propagate_errors:
                    raise ex
                else:
                    if (logger := get_audit_logger()) is not None:
                        # Temporarily disable the hook, since emitting a log could create new
                        # runtime events. In some cases this could lead to an infinite recursion.
                        with self.__disable_runtime_hook():
                            logger.error(
                                "%s raised in %s.sys_hook: %s",
                                ex.__class__.__name__,
                                self.__class__.__name__,
                                ex,
                            )

    @contextmanager
    def __disable_runtime_hook(self) -> t.Iterator[None]:
        """Temporarily the runtime hook."""
        is_active = self.__is_active
        self.__is_active = False
        try:
            yield None
        finally:
            self.__is_active = is_active

    @__update
    def prehook(
        self, event: str, args: t.Tuple[t.Any, ...], kwargs: t.Dict[str, t.Any]
    ) -> t.Optional[str]:
        old_event = self.__current_event
        self.__current_event = event
        return old_event

    def posthook(self, event: str, result: t.Any, context: t.Optional[str]) -> None:
        pass

    @__update
    def cleanup(self, event: str, context: t.Optional[str]) -> None:
        self.__current_event = context


RuntimeAuditHook.__init__.__doc__ = f"""\
Initialize the RuntimeAuditHook.

:param Optional[bool] propagate_errors: if not equal to ``None``, set the ``propagate_errors``
    attribute of the hook, which controls whether errors raised by :py:meth:`sys_hook` are
    propagated. Hooks for which ``propagate_errors`` is ``False`` will log errors raised by
    :py:meth:`sys_hook`, but won't raise them.

    By default, ``hook.propagate_errors = {RuntimeAuditHook.PROPAGATE_ERRORS_DEFAULT}`` for
    RuntimeAuditHooks.
"""
