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
2. Define new Seagrass events using ``Auditor.decorate`` or ``Auditor.wraps``.
3. Create a new auditing context using ``auditor.audit()``, and then start
   calling the code under audit.

Let's look at an example. Before we start, we'll configure the logger used by
Seagrass. Auditors default to using the ``"seagrass"`` logger, so we'll 
configure the logger to print all logs to ``stdout``:

.. code:: python

   import logging

   fh = logging.StreamHandler()
   fh.setLevel(logging.INFO)
   formatter = logging.Formatter("(%(levelname)s) %(message)s")
   fh.setFormatter(formatter)

   logger = logging.getLogger("seagrass")
   logger.setLevel(logging.INFO)
   logger.addHandler(fh)

Now let's use Seagrass! In the code below, we audit the ``add`` and ``sub``
functions to see how many times each of them are called. We create a new event
for the ``add`` function called ``event.add``, and an event for the ``sub``
function called ``event.sub``.

.. testsetup:: *

   import logging, sys
   from seagrass import Auditor

   fh = logging.StreamHandler(stream=sys.stdout)
   fh.setLevel(logging.INFO)
   formatter = logging.Formatter("(%(levelname)s) %(message)s")
   fh.setFormatter(formatter)

   logger = logging.getLogger("seagrass")
   logger.setLevel(logging.INFO)
   logger.addHandler(fh)

   auditor = Auditor()


.. testcode::

   from seagrass import Auditor
   from seagrass.hooks import CounterHook

   # Create a new Auditor instance
   auditor = Auditor()

   # Create a hook that will count each time an event occurs
   hook = CounterHook()

   # Now define some new events by hooking some example functions
   @auditor.decorate("event.add", hooks=[hook])
   def add(x: int, y: int) -> int:
       return x + y

   @auditor.decorate("event.sub", hooks=[hook])
   def sub(x: int, y: int) -> int:
       return x - y

   # Now start auditing!
   with auditor.audit():
       add(1, 2)
       add(3, 4)
       sub(5, 2)

   # Display the results of auditing.
   auditor.log_results()

.. testoutput::

   (INFO) Calls to events recorded by CounterHook:
   (INFO)     event.add: 2
   (INFO)     event.sub: 1

From here we can start doing more complicated tasks. For instance, here's an
example where we override Python's ``time.sleep`` and measure the amount of time
spent in that function (as well as the number of times it gets called).

.. doctest::

   >>> import time
   >>> from seagrass.hooks import CounterHook, TimerHook
   >>> ch = CounterHook()
   >>> th = TimerHook()
   >>> ausleep = auditor.wrap(time.sleep, "time.sleep", hooks=[ch,th])
   >>> time.sleep = ausleep
   >>> with auditor.audit():
   ...     for _ in range(10):
   ...         time.sleep(0.1)
   >>> auditor.log_results()  # doctest: +SKIP
   (INFO) Calls to events recorded by CounterHook:
   (INFO)     time.sleep: 10
   (INFO) TimerHook results:
   (INFO)     Time spent in time.sleep: 1.006210

---------------------
Defining custom hooks
---------------------

You can define your own hooks by creating a new class that implements the
``seagrass.base.ProtoHook`` interface.
