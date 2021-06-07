.. _glossary:

========
Glossary
========

-------
Auditor
-------

An instance of the ``seagrass.Auditor`` class. The auditor is the main external
interface for using Seagrass; you use it to select which parts of code you wish
to audit.

----------------
Auditing context
----------------

A block of code in which the local auditor is enabled. Typically you create a
new auditing context using :py:meth:`seagrass.Auditor.audit`:

.. testsetup:: auditing-context

   import seagrass

.. testcode:: auditing-context

   auditor = seagrass.Auditor()

   with auditor.audit():
       # Events that occur here will be audited
       ...

   # Events outside of the auditing context are not audited

You can also create an auditing context by enabling and disabling the auditor
with :py:meth:`seagrass.Auditor.toggle_auditing`:

.. testcode:: auditing-context

   auditor.toggle_auditing(True)

   # Events that occur here will be audited

   auditor.toggle_auditing(False)

   # Events here are not audited

-----
Event
-----

Also referred to as an *audit event*. Events (that is, instances of
:py:class:`seagrass.events.Event`) are the basic building block for auditing
code in Seagrass. You usually create an event with the list of hooks that you
want to run on that event using the ``@auditor.decorate`` or ``auditor.wrap``
methods of :py:class:`seagrass.Auditor`:

.. testsetup::

   from seagrass import Auditor
   auditor = Auditor()
   hooks = []

.. testcode::

   # Method 1: use @auditor.decorate to decorate a function definition.
   # This call will create a new event called "my_foo_event" whenever
   # we call the function foo
   @auditor.decorate("my_foo_event", hooks=hooks)
   def foo(x, y):
       return x + y

   # Method 2: use auditor.wrap to wrap an existing function.
   # This call will create a new event called "my_bar_event" whenever
   # we call the function audited_bar
   def bar(name):
       return f"Hello, {name}!"

   audited_bar = auditor.wrap(bar, "my_bar_event", hooks=hooks)

There are two main components to any event:

- The name of the event, represented by a string. Event names must be unique
  for each :py:class:`seagrass.Auditor`. If you try to define two events with
  the same name, you'll get an error:

  .. testsetup::
 
     from seagrass import Auditor
     auditor = Auditor()
     hooks = [] 
 
  .. doctest::
 
     >>> @auditor.decorate("my_event", hooks=hooks)
     ... def add(x, y):
     ...     return x + y
 
     >>> @auditor.decorate("my_event", hooks=hooks)
     ... def sub(x, y):
     ...     return x - y   # doctest: +IGNORE_EXCEPTION_DETAIL
     Traceback (most recent call last):
     ValueError: An event with the name 'my_event' has already been defined
 
- A function. The event is really just a wrapper around this function; instead
  of calling the function directly, we call the wrapper. If we're in an
  auditing context and the event is enabled (events can be toggled with
  :py:meth:`seagrass.Auditor.toggle_event`), then we will call the event's
  prehooks, call the function itself, and then call the event's posthooks.

---- 
Hook
----

A hook is an instance of a class that can be used to "hook" an event. It
primarily consists of a ``prehook`` and a ``posthook`` method, which are called
at the start and end of the event. Any class can be a hook so long as it
satisfies the :py:class:`seagrass.base.ProtoHook` protocol.

------------------------
Runtime audit event/hook
------------------------

The terms *runtime audit event* and *runtime audit hook* signify an audit
event/hook for the Python runtime as defined by `PEP 578`_. Runtime audit events
are created by calling ``sys.audit``, while runtime audit hooks are added with
``sys.addaudithook``.

These terms are used to differentiate between *Seagrass audit events/hooks*. A
Seagrass audit event is an instance of :py:class:`seagrass.events.Event`, while
a Seagrass audit hook is an instance of a class implementing the
:py:class:`seagrass.base.ProtoHook` protocol. Seagrass events and hooks are only
a part of the Seagrass library and not a part of the Python runtime.

While runtime audit events/hooks are similar to Seagrass events/hooks, they
share some important differences; see :ref:`faq_seagrass-vs-runtime-hooks` for
more information.

.. _PEP 578: https://www.python.org/dev/peps/pep-0578/
