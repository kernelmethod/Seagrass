.. _custom-hooks:

=====================
Creating custom hooks
=====================

A Seagrass audit hook is just a class satisfying the
:py:class:`seagrass.base.ProtoHook` interface. The easiest way to do this is to
create a new class that inherits from :py:class:`~seagrass.base.ProtoHook`.

Here is a basic example of a hook that just prints the arguments given to the
:py:meth:`~seagrass.base.ProtoHook.prehook` and
:py:meth:`~seagrass.base.ProtoHook.posthook` methods:

.. testsetup:: custom-hooks

   import time
   from seagrass import Auditor
   from seagrass.base import ProtoHook

   class ArgsHook(ProtoHook[None]):
       
       def prehook(self, event_name, args, kwargs):
           print(f"prehook: event_name={event_name!r}, args={args}, kwargs={kwargs}")

       def posthook(self, event_name, result, context):
           print(f"posthook: event_name={event_name!r}, result={result}, context={context}")

   class ElapsedTimeHook(ProtoHook[float]):
       def prehook(self, event_name, args, kwargs) -> float:
           print(f"Getting start time for {event_name}...")
           return time.time()
   
       def posthook(self, event_name, result, context: float):
           elapsed = time.time() - context
           end = time.time()
           print(f"Time spent in {event_name}: {elapsed:.1f}s")

   auditor = Auditor()

.. testcode::

   from seagrass.base import ProtoHook

   class ArgsHook(ProtoHook[None]):
       
       def prehook(self, event_name, args, kwargs) -> None:
           print(f"prehook: event_name={event_name!r}, args={args}, kwargs={kwargs}")

       def posthook(self, event_name, result, context: None):
           print(f"posthook: event_name={event_name!r}, result={result}, context={context}")

If you're using a typechecker like mypy, note that the type argument to
``ProtoHook`` is the type of the context returned by ``prehook`` (and used by
``posthook``).

This class satisfies the ``ProtoHook`` interface, so we can start using it to
hook events:

.. doctest:: custom-hooks

   >>> from seagrass import Auditor

   >>> auditor = Auditor()

   >>> hook = ArgsHook()

   >>> @auditor.audit("example.foo", hooks=[hook])
   ... def foo(x, y, z=0):
   ...     print(f"x + y + z = {x + y + z}")
   ...     return x + y + z

   >>> with auditor.start_auditing():
   ...     result = foo(2, -1, z=3)
   prehook: event_name='example.foo', args=(2, -1), kwargs={'z': 3}
   x + y + z = 4
   posthook: event_name='example.foo', result=4, context=None

------------------------------------------------
Passing context between the prehook and posthook
------------------------------------------------

Sometimes, we may want to calculate something in the prehook and pass the result
of our calculation to the posthook. For instance, consider an auditing hook that
reports the amount of time that was spent executing an event; the posthook would
need to know at what time the event started in order to figure out how much time
elapsed.

For cases like these, you can return a *context* variable from the prehook; this
variable is passed directly to ``posthook``. Here's an example where we
implement the hook mentioned before: the prehook returns the time at which it
was launched, which the posthook uses to calculate the total time spent
executing an event:

.. doctest:: custom-hooks

   >>> import time

   >>> class ElapsedTimeHook(ProtoHook[float]):
   ...     def prehook(self, event_name, args, kwargs) -> float:
   ...         print(f"Getting start time for {event_name}...")
   ...         return time.time()
   ...
   ...     def posthook(self, event_name, result, context: float):
   ...         elapsed = time.time() - context
   ...         end = time.time()
   ...         print(f"Time spent in {event_name}: {elapsed:.1f}s")
   ...

   >>> hook = ElapsedTimeHook()

   >>> ausleep = auditor.audit("event.sleep", time.sleep, hooks=[hook])

   >>> with auditor.start_auditing():
   ...     ausleep(0.1)
   Getting start time for event.sleep...
   Time spent in event.sleep: 0.1s

------------------------------------
Change prehook and posthook priority
------------------------------------

In some cases, it may make sense to have a hook run before or after other hooks
that have been assigned to an event. For instance, in our example above, we
probably want to have ``ElapsedTimeHook.prehook`` run *after* other
prehooks, and to have ``ElapsedTimeHook.posthook`` run *before* other
prehooks. This way, we wouldn't calculate the amount of time spent in other
hooks towards the total amount of time spent in the event.

Their are two ways to change the order in which hooks are run:

1. Change the order of the ``hooks`` list. When we call ``auditor.audit``, hooks
   hooks that come at the end of the list have their prehooks run *after* and
   their posthooks run *before* other events in the list.

   Here's what the output looks like if we put ``ElapsedTimeHook`` after
   ``ArgsHook``:

   .. doctest:: custom-hooks

      >>> hooks = [ArgsHook(), ElapsedTimeHook()]

      >>> ausleep = auditor.audit("sleep_ex_1", time.sleep, hooks=hooks)

      >>> with auditor.start_auditing():
      ...     ausleep(0.1)
      prehook: event_name='sleep_ex_1', args=(0.1,), kwargs={}
      Getting start time for sleep_ex_1...
      Time spent in sleep_ex_1: 0.1s
      posthook: event_name='sleep_ex_1', result=None, context=None

   And here's the output if we put ``ElapsedTimeHook`` before ``ArgsHook``:

   .. doctest:: custom-hooks

      >>> hooks = [ElapsedTimeHook(), ArgsHook()]

      >>> ausleep = auditor.audit("sleep_ex_2", time.sleep, hooks=hooks)

      >>> with auditor.start_auditing():
      ...     ausleep(0.1)
      Getting start time for sleep_ex_2...
      prehook: event_name='sleep_ex_2', args=(0.1,), kwargs={}
      posthook: event_name='sleep_ex_2', result=None, context=None
      Time spent in sleep_ex_2: 0.1s

2. Set a ``priority`` on your hooks (i.e. ``hook.priority``). Hooks with high
   priority will have their prehook executed *after* and its posthook executed
   *before* hooks with lower priority.

   .. doctest:: custom-hooks

      >>> th = ElapsedTimeHook()

      >>> ah = ArgsHook()

      >>> # Test with hook priority for ElapsedTimeHook

      >>> th.priority = 10

      >>> ausleep = auditor.audit("priority_ex", time.sleep, hooks=[th, ah])

      >>> with auditor.start_auditing():
      ...     ausleep(0.1)
      prehook: event_name='priority_ex', args=(0.1,), kwargs={}
      Getting start time for priority_ex...
      Time spent in priority_ex: 0.1s
      posthook: event_name='priority_ex', result=None, context=None


-----------------------
Additional hook methods
-----------------------

All hooks are required to define the methods specified by the
:py:class:`~seagrass.base.ProtoHook` protocol class. In addition, Seagrass
defines a few other protocols that your hook can implement to get even more
functionality.

- :py:class:`~seagrass.base.ResettableHook`: an interface that should be
  implemented for hooks that have some kind of internal state that should be
  able to be reset.
- :py:class:`~seagrass.base.LogResultsHook`: an interface for hooks whose
  results can be logged using :py:meth:`seagrass.Auditor.log_results`.
- :py:class:`~seagrass.base.CleanupHook`: an interface for hooks that have a
  "clean-up" stage that needs to be executed before an event is finished.

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
:py:class:`~seagrass.base.ResettableHook`: resetting hooks with internal state
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sometimes, you may want to perform multiple auditing runs, and report the
results from each run. Here's an example where we use
:py:class:`seagrass.hooks.CounterHook` to count the number of times the event
``"audit.foo"`` gets raised:

.. testsetup:: resettable-hook-example

   from seagrass import Auditor
   from seagrass._docs import configure_logging

   configure_logging()
   auditor = Auditor()

.. doctest:: resettable-hook-example

   >>> from seagrass.hooks import CounterHook

   >>> hook = CounterHook()

   >>> ev_foo = auditor.create_event("audit.foo", hooks=[hook])

   >>> with auditor.start_auditing():
   ...     auditor.raise_event("audit.foo")

   >>> auditor.log_results()
   (INFO) seagrass: Calls to events recorded by CounterHook:
   (INFO) seagrass:     audit.foo: 1

   >>> with auditor.start_auditing():
   ...     auditor.raise_event("audit.foo")

   >>> auditor.log_results()
   (INFO) seagrass: Calls to events recorded by CounterHook:
   (INFO) seagrass:     audit.foo: 2


Notice that the second time we called ``log_results``, it contained the results
for both the first auditing context and the second auditing context. If we want
to reset results between runs, we need to call ``hook.reset()``:

.. doctest:: resettable-hook-example

   >>> hook.reset()

   >>> with auditor.start_auditing():
   ...     auditor.raise_event("audit.foo")

   >>> auditor.log_results()
   (INFO) seagrass: Calls to events recorded by CounterHook:
   (INFO) seagrass:     audit.foo: 1

Alternatively, we could pass ``reset_hooks=True`` and ``log_results=True`` when
we call ``auditor.audit``. This logs all hook results and then resets the hooks
when we leave the auditing context:

.. doctest:: resettable-hook-example

   >>> hook.reset()

   >>> with auditor.start_auditing(reset_hooks=True, log_results=True):
   ...     auditor.raise_event("audit.foo")
   (INFO) seagrass: Calls to events recorded by CounterHook:
   (INFO) seagrass:     audit.foo: 1

   >>> # Since the hooks were reset, log_results won't show any recorded events

   >>> auditor.log_results()
   (INFO) seagrass: Calls to events recorded by CounterHook:
   (INFO) seagrass:     (no events recorded)

A hook that implements the :py:class:`~seagrass.base.ResettableHook` interface
by implementing :py:meth:`~seagrass.base.ResettableHook.reset` can be reset
using ``auditor.reset_hooks()`` or by passing ``reset_hooks=True`` into
``auditor.start_auditing()``. For most hooks that have some kind of mutable
internal state, you probably want to implement this interface.

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
:py:class:`~seagrass.base.LogResultsHook`: logging your hook's results
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Hooks that implement the :py:class:`seagrass.base.LogResultsHook` interface (in
addition to :py:class:`~seagrass.base.ProtoHook` will also have their results
logged when ``auditor.log_results()`` is called.

.. testsetup::

   from seagrass import Auditor
   from seagrass.base import ProtoHook
   from seagrass._docs import configure_logging

   configure_logging()
   auditor = Auditor()

.. doctest::

   >>> import time

   >>> class TotalElapsedTimeHook(ProtoHook[float]):
   ...      def __init__(self):
   ...          self.ctr = 0.
   ...
   ...      def prehook(self, event_name, args, kwargs) -> float:
   ...          return time.time()
   ...
   ...      def posthook(self, event_name, result, context: float):
   ...          start_time = context
   ...          self.ctr += time.time() - start_time
   ...
   ...      def log_results(self, logger):
   ...          logger.info("TotalElapsedTimeHook: elapsed time: %.1fs", self.ctr)

   >>> hook = TotalElapsedTimeHook()

   >>> time.sleep = auditor.audit("event.sleep", time.sleep, hooks=[hook])

   >>> with auditor.start_auditing():
   ...     time.sleep(0.1)

   >>> auditor.log_results()
   (INFO) seagrass: TotalElapsedTimeHook: elapsed time: 0.1s

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
:py:class:`~seagrass.base.CleanupHook`: hooks with a cleanup stage
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Some hooks may have side effects that need to be cleaned up after the hook is
executed. For instance, here is a hook that sets the ``CURRENT_EVENT`` global
variable to be the name of the current Seagrass event that is executing (or
``None`` if no event is being executed):

.. testsetup:: cleanup-hook-examples

   from seagrass import Auditor
   auditor = Auditor()

.. doctest:: cleanup-hook-examples

    >>> from seagrass.base import ProtoHook

    >>> import typing as t

    >>> CURRENT_EVENT: t.Optional[str] = None

    >>> class BadCurrentEventHook(ProtoHook):
    ...      def prehook(self, event_name, args, kwargs):
    ...          global CURRENT_EVENT
    ...          old_event = CURRENT_EVENT
    ...          CURRENT_EVENT = event_name
    ...          return old_event
    ...
    ...      def posthook(self, event_name, result, context):
    ...          global CURRENT_EVENT
    ...          old_event = context
    ...          CURRENT_EVENT = old_event

    >>> hook = BadCurrentEventHook()

    >>> print_event = lambda: print(f"CURRENT_EVENT={CURRENT_EVENT!r}")

    >>> foo = auditor.audit("event.foo", print_event, hooks=[hook])

    >>> bar = auditor.audit("event.bar", print_event, hooks=[hook])

    >>> with auditor.start_auditing():
    ...     foo()
    ...     bar()
    CURRENT_EVENT='event.foo'
    CURRENT_EVENT='event.bar'

    >>> print(CURRENT_EVENT)
    None

However, what happens if an exception is raised while we're running the event
that's being executed? In that case, the posthook never executes, and
``CURRENT_EVENT`` doesn't get reset back to its old value:

.. doctest:: cleanup-hook-examples

   >>> @auditor.audit("event.baz", hooks=[hook])
   ... def baz():
   ...     raise RuntimeError()

   >>> with auditor.start_auditing():
   ...     baz() # doctest: +IGNORE_EXCEPTION_DETAIL
   Traceback (most recent call last):
   RuntimeError:

   >>> print(CURRENT_EVENT)
   event.baz


What we should do instead is define a
:py:meth:`~seagrass.base.CleanupHook.cleanup` method so that our hook satisfies
the :py:class:`~seagrass.base.CleanupHook` interface, and then reset the value
of ``CURRENT_EVENT`` in ``cleanup()``. Unlike ``posthook``, the ``cleanup``
stage of a hook is called no matter what, so long as the hook's ``prehook`` was
executed.


.. testsetup:: cleanup-hook-examples-2

   import typing as t
   CURRENT_EVENT = None

.. doctest:: cleanup-hook-examples-2

   >>> import seagrass

   >>> from seagrass.base import ProtoHook, CleanupHook

   >>> class CurrentEventHook(ProtoHook):
   ...      def prehook(self, event_name, args, kwargs):
   ...          global CURRENT_EVENT
   ...          old_event = CURRENT_EVENT
   ...          CURRENT_EVENT = event_name
   ...          return old_event
   ...
   ...      def cleanup(self, event_name, context, exc):
   ...          global CURRENT_EVENT
   ...          old_event = context
   ...          CURRENT_EVENT = old_event

   >>> hook = CurrentEventHook()

   >>> isinstance(hook, CleanupHook)
   True

By deferring the part where we reset ``CURRENT_EVENT`` to the ``cleanup``
function, we ensure that ``CURRENT_EVENT`` will always be reset even if an
exception is raised during the execution of the audited event:

.. doctest:: cleanup-hook-examples-2

   >>> import seagrass

   >>> @seagrass.audit("event.baz", hooks=[hook])
   ... def baz():
   ...     raise RuntimeError()

   >>> with seagrass.start_auditing():
   ...     baz() # doctest: +IGNORE_EXCEPTION_DETAIL
   Traceback (most recent call last):
   RuntimeError:

   >>> print(CURRENT_EVENT)
   None
