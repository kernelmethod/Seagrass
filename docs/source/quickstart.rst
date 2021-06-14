.. _quick-start-guide:

=================
Quick start guide
=================

------------
Installation
------------

You can install the latest version of Seagrass by running

.. code::

   pip install seagrass

-------------------------------
Creating a new Auditor
-------------------------------

You typically audit code with Seagrass in three steps:

1. Create a new ``Auditor`` instance.
2. Define new Seagrass events using ``Auditor.audit``.
3. Create a new auditing context using ``auditor.start_auditing()``, and then
   start calling the code under audit.

Let's look at an example. Before we start, we'll configure the logger used by
Seagrass. Auditors default to using the ``"seagrass"`` logger, so we'll 
configure the logger to print all logs to ``stdout``:

.. code:: python

   import logging

   fh = logging.StreamHandler()
   fh.setLevel(logging.INFO)
   formatter = logging.Formatter("(%(levelname)s) %(name)s: %(message)s")
   fh.setFormatter(formatter)

   logger = logging.getLogger("seagrass")
   logger.setLevel(logging.INFO)
   logger.addHandler(fh)

Now let's use Seagrass! In the code below, we audit the ``add`` and ``sub``
functions to see how many times each of them are called. We create a new event
for the ``add`` function called ``event.add``, and an event for the ``sub``
function called ``event.sub``.

.. testsetup:: basic-quickstart-example

   import logging, sys
   from seagrass import Auditor

   fh = logging.StreamHandler(stream=sys.stdout)
   fh.setLevel(logging.INFO)
   formatter = logging.Formatter("(%(levelname)s) %(name)s: %(message)s")
   fh.setFormatter(formatter)

   logger = logging.getLogger("seagrass")
   logger.setLevel(logging.INFO)
   logger.addHandler(fh)

   auditor = Auditor()


.. testcode:: basic-quickstart-example

   from seagrass import Auditor
   from seagrass.hooks import CounterHook

   # Create a new Auditor instance
   auditor = Auditor()

   # Create a hook that will count each time an event occurs
   hook = CounterHook()

   # Now define some new events by hooking some example functions
   @auditor.audit("event.add", hooks=[hook])
   def add(x: int, y: int) -> int:
       return x + y

   @auditor.audit("event.sub", hooks=[hook])
   def sub(x: int, y: int) -> int:
       return x - y

   # Now start auditing!
   with auditor.start_auditing():
       add(1, 2)
       add(3, 4)
       sub(5, 2)

   # Display the results of auditing.
   auditor.log_results()

.. testoutput:: basic-quickstart-example

   (INFO) seagrass: Calls to events recorded by CounterHook:
   (INFO) seagrass:     event.add: 2
   (INFO) seagrass:     event.sub: 1

From here we can start doing more complicated tasks. For instance, here's an
example where we override Python's ``time.sleep`` and measure the amount of time
spent in that function (as well as the number of times it gets called).

.. doctest:: basic-quickstart-example

   >>> import time
   >>> from seagrass.hooks import CounterHook, TimerHook
   >>> ch = CounterHook()
   >>> th = TimerHook()
   >>> ausleep = auditor.audit("time.sleep", time.sleep, hooks=[ch,th])
   >>> time.sleep = ausleep
   >>> with auditor.start_auditing():
   ...     for _ in range(10):
   ...         time.sleep(0.1)
   >>> auditor.log_results()  # doctest: +SKIP
   (INFO) seagrass: Calls to events recorded by CounterHook:
   (INFO) seagrass:    time.sleep: 10
   (INFO) seagrass: TimerHook results:
   (INFO) seagrass:    Time spent in time.sleep: 1.006210

-----------------------------------------------
Raising audit events without wrapping functions
-----------------------------------------------

Up until this point, we've been creating audit events by calling
:py:meth:`seagrass.Auditor.audit` function that we want to audit. Sometimes,
though, it doesn't make sense to audit an entire function; perhaps we just want
to raise a signal at a single point in time, and have Seagrass capture
information about that signal.

We can achieve this functionality by using
:py:meth:`~seagrass.Auditor.create_event` and
:py:meth:`~seagrass.Auditor.raise_event`. In the code snippet below, we create a
new event ``my_sum.cumsum`` and call it at every iteration of the function
``my_sum`` to get the cumulative sum that's being calculated internally.

.. testsetup:: empty-auditing-events

   import logging, sys
   from seagrass import Auditor

   fh = logging.StreamHandler(stream=sys.stdout)
   fh.setLevel(logging.DEBUG)
   formatter = logging.Formatter("(%(levelname)s) %(name)s: %(message)s")
   fh.setFormatter(formatter)

   logger = logging.getLogger("seagrass")
   logger.setLevel(logging.DEBUG)
   logger.addHandler(fh)

   auditor = Auditor(logger=logger)

.. doctest:: empty-auditing-events

   >>> from seagrass.hooks import LoggingHook

   >>> prehook_msg = lambda event_name, args, kwargs: f"cumsum={args[0]}"

   >>> hook = LoggingHook(prehook_msg=prehook_msg)

   >>> event_wrapper = auditor.create_event("my_sum.cumsum", hooks=[hook])

   >>> def my_sum(iterable):
   ...     total = 0.
   ...     for val in iterable:
   ...         auditor.raise_event("my_sum.cumsum", total)
   ...         total += val
   ...     return total

   >>> with auditor.start_auditing():
   ...     my_sum([1, 2, 3, 4])
   (DEBUG) seagrass: cumsum=0.0
   (DEBUG) seagrass: cumsum=1.0
   (DEBUG) seagrass: cumsum=3.0
   (DEBUG) seagrass: cumsum=6.0
   10.0
