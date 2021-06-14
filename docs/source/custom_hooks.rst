.. _custom-hooks:

=====================
Creating custom hooks
=====================

A Seagrass audit hook is just a class satisfying the
:py:class:`seagrass.base.ProtoHook` interface. Here is a basic example of a hook
that just prints the arguments given to the
:py:meth:`~seagrass.base.ProtoHook.prehook` and
:py:meth:`~seagrass.base.ProtoHook.posthook` methods:

.. testsetup:: custom-hooks

   import time
   from seagrass import Auditor

   class ArgsHook:
       
       def prehook(self, event_name, args, kwargs):
           print(f"ArgsHook: prehook: {event_name=}, {args=}, {kwargs=}")

       def posthook(self, event_name, result, context):
           print(f"ArgsHook: posthook: {event_name=}, {result=}, {context=}")

   class ElapsedTimeHook:
       def prehook(self, event_name, args, kwargs) -> float:
           print(f"ElapsedTimeHook: Getting start time for {event_name}...")
           return time.time()
   
       def posthook(self, event_name, result, context: float):
           elapsed = time.time() - context
           end = time.time()
           print(f"ElapsedTimeHook: Time spent in {event_name}: {elapsed:.1f}s")

   auditor = Auditor()

.. testcode::

   class ArgsHook:
       
       def prehook(self, event_name, args, kwargs):
           print(f"ArgsHook: prehook: {event_name=}, {args=}, {kwargs=}")

       def posthook(self, event_name, result, context):
           print(f"ArgsHook: posthook: {event_name=}, {result=}, {context=}")

This class satisfies the ``ProtoHook`` interface, so we can start using it to
hook events:

.. doctest:: custom-hooks

   >>> from seagrass import Auditor

   >>> auditor = Auditor()

   >>> hook = ArgsHook()

   >>> @auditor.audit("example.foo", hooks=[hook])
   ... def foo(x, y, z=0):
   ...     print(f"{x + y + z = }")
   ...     return x + y + z

   >>> with auditor.start_auditing():
   ...     result = foo(2, -1, z=3)
   ArgsHook: prehook: event_name='example.foo', args=(2, -1), kwargs={'z': 3}
   x + y + z = 4
   ArgsHook: posthook: event_name='example.foo', result=4, context=None

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

   >>> class ElapsedTimeHook:
   ...     def prehook(self, event_name, args, kwargs) -> float:
   ...         print(f"ElapsedTimeHook: Getting start time for {event_name}...")
   ...         return time.time()
   ...
   ...     def posthook(self, event_name, result, context: float):
   ...         elapsed = time.time() - context
   ...         end = time.time()
   ...         print(f"ElapsedTimeHook: Time spent in {event_name}: {elapsed:.1f}s")
   ...

   >>> hook = ElapsedTimeHook()

   >>> ausleep = auditor.audit("event.sleep", time.sleep, hooks=[hook])

   >>> with auditor.start_auditing():
   ...     ausleep(0.1)
   ElapsedTimeHook: Getting start time for event.sleep...
   ElapsedTimeHook: Time spent in event.sleep: 0.1s

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
      ArgsHook: prehook: event_name='sleep_ex_1', args=(0.1,), kwargs={}
      ElapsedTimeHook: Getting start time for sleep_ex_1...
      ElapsedTimeHook: Time spent in sleep_ex_1: 0.1s
      ArgsHook: posthook: event_name='sleep_ex_1', result=None, context=None

   And here's the output if we put ``ElapsedTimeHook`` before ``ArgsHook``:

   .. doctest:: custom-hooks

      >>> hooks = [ElapsedTimeHook(), ArgsHook()]

      >>> ausleep = auditor.audit("sleep_ex_2", time.sleep, hooks=hooks)

      >>> with auditor.start_auditing():
      ...     ausleep(0.1)
      ElapsedTimeHook: Getting start time for sleep_ex_2...
      ArgsHook: prehook: event_name='sleep_ex_2', args=(0.1,), kwargs={}
      ArgsHook: posthook: event_name='sleep_ex_2', result=None, context=None
      ElapsedTimeHook: Time spent in sleep_ex_2: 0.1s

2. Set a ``prehook_priority`` and/or ``posthook_priority`` on your hooks.
   Seagrass calls :py:func:`seagrass.base.prehook_priority` and
   :py:func:`seagrass.base.posthook_priority` on audit hooks to see if they
   have an explicit priority set for them. For hooks that don't have a priority
   set, their priority is assumed to be the default value of ``0``.

   ``prehook_priority`` and ``posthook_priority`` are interpreted as follows:

   - If you set ``hook.prehook_priority`` to be high, its prehook will be
     executed *after* prehooks with lower priority.
   - If you set ``hook.posthook_priority`` to be low, its prehook will be
     executed *before* posthooks with lower priority.

   The rationale here is that priority signals how closely a prehook or posthook
   should be executed relative to when the function wrapped by an event is
   called. For profiling-related hooks this is especially important, since
   ideally a profiling hook should only collect statistics from the execution of
   an event and not from the execution of other hooks.

   .. doctest:: custom-hooks

      >>> th = ElapsedTimeHook()

      >>> ah = ArgsHook()

      >>> # Test with high prehook and posthook priorities for ElapsedTimeHook

      >>> th.prehook_priority = 10; th.posthook_priority = 10;

      >>> ausleep = auditor.audit("priority_ex_1", time.sleep, hooks=[th, ah])

      >>> with auditor.start_auditing():
      ...     ausleep(0.1)
      ArgsHook: prehook: event_name='priority_ex_1', args=(0.1,), kwargs={}
      ElapsedTimeHook: Getting start time for priority_ex_1...
      ElapsedTimeHook: Time spent in priority_ex_1: 0.1s
      ArgsHook: posthook: event_name='priority_ex_1', result=None, context=None

      >>> # Test with low prehook/high posthook priority

      >>> th.prehook_priority = -10

      >>> ausleep = auditor.audit("priority_ex_2", time.sleep, hooks=[th, ah])

      >>> with auditor.start_auditing():
      ...     ausleep(0.1)
      ElapsedTimeHook: Getting start time for priority_ex_2...
      ArgsHook: prehook: event_name='priority_ex_2', args=(0.1,), kwargs={}
      ElapsedTimeHook: Time spent in priority_ex_2: 0.1s
      ArgsHook: posthook: event_name='priority_ex_2', result=None, context=None


-----------------------
Additional hook methods
-----------------------

All hooks are required to define the methods specified by the
:py:class:`~seagrass.base.ProtoHook` protocol class. In addition, Seagrass
defines a few other protocols that your hook can implement to get even more
functionality.

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
:py:class:`~seagrass.base.ResettableHook`: resetting hooks with internal state
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sometimes, you may want to perform multiple auditing runs, and report the
results from each run. Here's an example where we use
:py:class:`seagrass.hooks.CounterHook` to count the number of times the event
``"audit.foo"`` gets raised:

.. testsetup:: resettable-hook-example

   import logging, sys
   from seagrass import Auditor

   fh = logging.StreamHandler(stream=sys.stdout)
   fh.setLevel(logging.INFO)
   formatter = logging.Formatter("(%(levelname)s) %(name)s: %(message)s")
   fh.setFormatter(formatter)

   logger = logging.getLogger("seagrass")
   logger.handlers = []
   logger.setLevel(logging.INFO)
   logger.addHandler(fh)

   auditor = Auditor(logger=logger)

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

   import logging, sys
   from seagrass import Auditor

   fh = logging.StreamHandler(stream=sys.stdout)
   fh.setLevel(logging.INFO)
   formatter = logging.Formatter("(%(levelname)s) %(name)s: %(message)s")
   fh.setFormatter(formatter)

   logger = logging.getLogger("seagrass")
   logger.setLevel(logging.INFO)
   logger.addHandler(fh)

   auditor = Auditor(logger=logger)

.. doctest::

   >>> import time

   >>> class TotalElapsedTimeHook:
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

