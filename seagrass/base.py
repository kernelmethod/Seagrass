import logging
import typing as t

# Type variable for contexts returned by prehooks
C = t.TypeVar("C")

DEFAULT_PREHOOK_PRIORITY: int = 0
DEFAULT_POSTHOOK_PRIORITY: int = 0


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
        ...     def prehook(self, event_name, args, kwargs):
        ...         assert isinstance(args[0], str), "Input must be type str"
        ...
        ...     def posthook(self, event_name, result, context):
        ...         pass

        >>> @auditor.audit("event.say_hello", hooks=[TypeCheckHook()])
        ... def say_hello(name: str):
        ...     return f"Hello, {name}!"

        >>> with auditor.start_auditing():
        ...     say_hello("Alice")
        ...     say_hello(0)    # Should raise AssertionError   # doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
        AssertionError: Input must be type str
    """

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

    def posthook(self, event_name: str, result: t.Any, context: C) -> None:
        """Run the posthook. The posthook is run at the end of the execution of
        an audited event, after the function wrapped by the event is run.

        :param str event_name: The name of the event that was triggered.
        :param Any result: The value that was returned by the event's wrapped function.
        :param C context: The context that was returned by the original call to ``prehook``.
        """


def prehook_priority(hook: ProtoHook) -> int:
    priority = getattr(hook, "prehook_priority", DEFAULT_PREHOOK_PRIORITY)
    if not isinstance(priority, int):
        raise TypeError(f"prehook_priority for {hook} must be an integer")
    return priority


prehook_priority.__doc__ = f"""\
Get the priority in which the prehook should be executed. Prehooks are executed in
*ascending* order of their priority, i.e. prehooks with low ``prehook_priority``
are executed *before* those with high ``prehook_priority``.

If ``hook.prehook_priority`` is defined, its value is used as the priority; otherwise
the default priority ``{DEFAULT_PREHOOK_PRIORITY=}`` is used.

:param ProtoHook hook: the hook whose prehook priority should be retrieved.
:return: the priority of the prehook.
:rtype: int
:raises TypeError: if ``hook.prehook_priority`` is set to a non-integer value.
"""


def posthook_priority(hook: ProtoHook) -> int:
    priority = getattr(hook, "posthook_priority", DEFAULT_POSTHOOK_PRIORITY)
    if not isinstance(priority, int):
        raise TypeError(f"posthook_priority for {hook} must be an integer")
    return priority


posthook_priority.__doc__ = f"""\
Get the priority in which the posthook should be executed. Posthooks are executed in
*descending* order of their priority, i.e. posthooks with low ``posthook_priority``
are executed *after* those with high ``posthook_priority``.

If ``hook.posthook_priority`` is defined, its value is used as the priority; otherwise
the default priority ``{DEFAULT_POSTHOOK_PRIORITY=}`` is used.

:param ProtoHook hook: the hook whose posthook priority should be retrieved.
:return: the priority of the posthook.
:rtype: int
:raises TypeError: if ``hook.posthook_priority`` is set to a non-integer value.
"""


@t.runtime_checkable
class LogResultsHook(t.Protocol):
    """A protocol class for hooks that support an additional `log_results` method that
    outputs the results of the hook."""

    def log_results(
        self,
        logger: logging.Logger,
    ) -> None:
        """Log results that have been accumulated by the hook using the provided logger.

        :param logging.Logger logger: the logger that should be used to output results.
        """


@t.runtime_checkable
class ResettableHook(t.Protocol):
    """A protocol class for hooks that can be reset.

    **Examples:** here is a minimal example of a Seagrass hook that satisfies the
    ``ResettableHook`` interface. Every time the event ``"my_event"`` is raised,
    the hook prints the number of times the event has been raised so far and
    increments its counter.

    .. doctest::

       >>> from seagrass.base import ResettableHook

       >>> class PrintEventHook:
       ...     def __init__(self):
       ...         self.reset()
       ...
       ...     def prehook(self, event_name, *args):
       ...         if event_name == "my_event":
       ...             self.event_counter += 1
       ...             print(f"my_event has be raised {self.event_counter} times")
       ...
       ...     def posthook(self, *args):
       ...         pass
       ...
       ...     def reset(self):
       ...         self.event_counter = 0
       ...

       >>> hook = PrintEventHook()

       >>> isinstance(hook, ResettableHook)
       True
    """

    def reset(self) -> None:
        """Reset the internal state of the hook."""


@t.runtime_checkable
class CleanupHook(ProtoHook[C], t.Protocol[C]):
    """A protocol class for hooks that have a 'cleanup' stage.

    Hooks that implement this interface are unconditionally 'cleaned up' after an event if their
    prehook was run during that event. Hooks that modify their internal state or create other
    side effects that need to be reset after the event is finished executing should implement
    this interface, in case an exception is thrown during the course of the event.
    """

    def cleanup(self, event_name: str, context: C):
        """Perform the hook's cleanup stage. The ``event_name`` and ``context`` are the same as
        those used by the ``posthook`` function."""
