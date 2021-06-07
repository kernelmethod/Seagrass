import logging
import typing as t

# Type variable for contexts returned by prehooks
C = t.TypeVar("C")


class ProtoHook(t.Protocol[C]):
    """Interface for hooks that can be used by Seagrass. New Seagrass hooks must define all of
    the properties and methods required for this class.

    Here's an example of a minimal hook that satisfies the ProtoHook interface. All this hook
    does is make an assertion that the first argument to a function wrapped by an audited
    event is a string.

    .. testsetup:: example_impl

        from seagrass import Auditor
        auditor = Auditor()

    .. doctest:: example_impl

        >>> class TypeCheckHook:
        ...     prehook_priority: int = 0
        ...     posthook_priority: int = 0
        ...
        ...     def prehook(self, event_name, args, kwargs):
        ...         assert isinstance(args[0], str), "Input must be type str"
        ...
        ...     def posthook(self, event_name, result, context):
        ...         pass
        ...
        ...     def reset(self):
        ...         pass

        >>> @auditor.decorate("event.say_hello", hooks=[TypeCheckHook()])
        ... def say_hello(name: str):
        ...     return f"Hello, {name}!"

        >>> with auditor.audit():
        ...     say_hello("Alice")
        ...     say_hello(0)    # Should raise AssertionError   # doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
        AssertionError: Input must be type str
    """

    @property
    def prehook_priority(self) -> int:
        """The priority in which the prehook should be executed. Prehooks are executed in
        *ascending* order of their priority, i.e. prehooks with low ``prehook_priority``
        are executed *before* those with high ``prehook_priority``.

        :type: int
        """
        ...

    @property
    def posthook_priority(self) -> int:
        """The priority in which the posthook should be executed. Posthooks are executed in
        *descending* order of their priority, i.e. posthooks with low ``posthook_priority``
        are executed *after* those with high ``posthook_priority``.

        :type: int
        """
        ...

    def prehook(
        self, event_name: str, args: t.Tuple[t.Any, ...], kwargs: t.Dict[str, t.Any]
    ) -> C:
        """Run the prehook. The prehook is run at the beginning of the execution of
        an audited event, before the function wrapped by the event is run.

        :param str event_name: The name of the event that was triggered.
        :param Tuple[Any,...] args: A tuple of the arguments passed to the function wrapped by
            the event.
        :param Dict[str,Any] kwargs: A dictionary of the keyword arguments passed to the function
            wrapped by the event.
        :return: "context" data that can be used by the posthook.
        :rtype: C
        """
        ...

    def posthook(self, event_name: str, result: t.Any, context: C):
        """Run the posthook. The posthook is run at the end of the execution of
        an audited event, after the function wrapped by the event is run.

        :param str event_name: The name of the event that was triggered.
        :param Any result: The value that was returned by the event's wrapped function.
        :param C context: The context that was returned by the original call to ``prehook``.
        """
        ...

    def reset(self):
        """Resets the internal state of the hook, if there is any."""
        ...


@t.runtime_checkable
class LoggableHook(t.Protocol):
    """A mixin class for hooks that support an additional `log_results` method that
    outputs the results of the hook."""

    def log_results(
        self,
        logger: logging.Logger,
    ):
        """Log results that have been accumulated by the hook using the provided logger.

        :param logging.Logger logger: the logger that should be used to output results.
        """
        ...
