import seagrass._typing as t
from seagrass.base import ProtoHook
from types import TracebackType

C = t.TypeVar("C")
CtxType = t.Optional[t.ContextManager[C]]


class ContextManagerHook(ProtoHook[CtxType[C]]):
    """A hook that wraps around a context manager, calling the context manager's ``__enter__`` and
    ``__exit__`` methods whenever the hook is activated."""

    __current_cm: t.Optional[t.ContextManager[C]] = None

    @property
    def current_context_manager(self) -> t.Optional[t.ContextManager[C]]:
        """Return the current context manager instance being used by the hook."""
        return self.__current_cm

    @property
    def is_active(self) -> bool:
        """Returns ``True`` if an event that uses this hook is currently being executed."""
        return self.current_context_manager is not None

    def __init__(
        self,
        cm: t.Union[t.ContextManager[C], t.Callable[[], t.ContextManager[C]]],
        nest: bool = False,
    ) -> None:
        """Create a new :py:class:`ContextManagerHook`.

        :param t.Union[t.ContextManager, t.Callable[[], t.ContextManager]] cm: a context manager
            (i.e., an object with ``__enter__`` and ``__exit__`` methods) or a function that takes
            no arguments and creates a new context manager.
        :param bool nest: whether successive invocations of the context manager should be nested.
            If ``nest=False`` and another Seagrass event that uses this hook gets called, the
            prehook and cleanup stages of the hook will be skipped. In general, you should set
            ``nest=True`` if your context manager should be used along the lines of

                .. code::

                    with cm:
                        # Execute outer event
                        ...
                        with cm:
                            # Execute inner event
                            ...
                        # Continue executing outer event
                        ...

            and ``nest=False`` if your context manager should be used as

                .. code::

                    with cm:
                        # Execute outer event
                        ...
                        # Execute inner event
                        ...
                        # Continue executing outer event
                        ...
        """
        self.cm = cm
        self.nest = nest

    def __create_cm(self) -> t.ContextManager[C]:
        if isinstance(self.cm, t.ContextManager):
            return self.cm
        else:
            return self.cm()

    def prehook(
        self, event: str, args: t.Tuple[t.Any, ...], kwargs: t.Dict[str, t.Any]
    ) -> CtxType[C]:
        if self.nest or self.current_context_manager is None:
            cm = self.__create_cm()
            cm.__enter__()
        else:
            cm = self.current_context_manager

        old_cm = self.current_context_manager
        self.__current_cm = cm
        return old_cm

    def cleanup(
        self,
        event: str,
        context: CtxType[C],
        exc: t.Tuple[
            t.Optional[t.Type[BaseException]],
            t.Optional[BaseException],
            t.Optional[TracebackType],
        ],
    ) -> None:
        old_cm = context
        current_cm = self.current_context_manager
        self.__current_cm = old_cm

        if (self.nest or not self.is_active) and current_cm is not None:
            exc_type, exc_val, tb = exc
            current_cm.__exit__(exc_type, exc_val, tb)
