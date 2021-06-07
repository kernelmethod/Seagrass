.. _faq:

===
FAQ
===

.. _faq_seagrass-vs-runtime-hooks:

-------------------------------------------------------
Why use Seagrass instead of Python runtime audit hooks?
-------------------------------------------------------

`PEP 578`_ introduced *Python runtime audit hooks*, which can be used by
auditing tools to monitor events taken by the Python runtime. In particular, as
of Python 3.8 you can use ``sys.audit(event: str, *args)`` to raise a new
runtime audit event, and ``sys.addaudithook(hook: Callable[[str,tuple]])`` to
add a new audit hook that inspects these events.

On its face, runtime audit events hooks are very similar to the event and
hooking mechanisms offered by Seagrass, so it might not be immediately apparent
why one would want to use Seagrass instead of runtime audit hooks. Indeed, you
could replicate most of the functionality of Seagrass just by using sufficiently
complex runtime hooks. However, Seagrass has a few built-in features that make
it more useful than runtime hooking:

- **Pre-/post-hooking:** Seagrass audit hooks (which implement the
  ``seagrass.base.ProtoHook`` interface) have a ``prehook`` and a ``posthook``
  method that get called before and after an event is raised; runtime audit
  hooks added with ``sys.addaudithook`` only get called when ``sys.audit`` is
  called. This makes Seagrass hooks a little more flexible: you can hook both
  the start and end of a function, including all of its inputs and outputs,
  while passing additional context data between the prehook and posthook.

- **Toggling hooks and events:** Seagrass hooks are only run when an event using
  those hooks is called, and only if (a) the event is executed inside of an
  auditing context and (b) when the event has not been disabled. In contrast,
  once a runtime audit hook has been added with ``sys.addaudithook``, it is
  difficult if not impossible to remove them (see this blog post, `Bypassing
  Python3.8 Audit Hooks`_, for more information). As a result, Seagrass provides
  many more options for selecting which part of your code you want to audit, and
  less overhead than runtime audit hooks.

- **Built-in hooks:** Seagrass comes with a handful of different useful hooks
  built-in through the :py:mod:`seagrass.hooks` module. If you want to use
  runtime hooks, you have to define them from scratch.

Note that Seagrass is highly compatible with runtime audit hooks. In fact, you
can use Seagrass as a thin layer around ``sys.audit`` by passing
``raise_runtime_events=True`` when you create a new event:

.. testsetup:: raise-runtime-events

   from seagrass import Auditor
   auditor = Auditor()

.. testcode:: raise-runtime-events

   @auditor.decorate("foo_event", raise_runtime_events=True)
   def foo(x, y, z=0):
       return x + y + z

The code snippet above created a new Seagrass event, ``"foo_event"``, that
doesn't actually call any Seagrass hooks. Instead, whenever we call ``foo``, two
new runtime events are raised by ``sys.audit``:

- ``prehook:foo_event``: this event is raised *before* the body of ``foo`` is
  run. This event is provided with two arguments: ``args`` (the arguments to the
  function ``foo``) and ``kwargs`` (the keyword arguments to ``foo``).
- ``posthook:foo_event``: this event is raised *after* the body of ``foo`` is
  run. This event is provided with one argument: ``result`` (the value returned
  by ``foo``).

Here's an example where we add a new runtime hook that prints whenever one of
these events is raised, along with the arguments passed to ``sys.audit``:

.. doctest:: raise-runtime-events

   >>> import sys

   >>> def foo_event_hook(event, args):
   ...     if event == "prehook:foo_event":
   ...         args, kwargs = args
   ...         print(f"prehook called: {args=}, {kwargs=}")
   ...     elif event == "posthook:foo_event":
   ...         result = args[0]
   ...         print(f"posthook called: {result=}")

   >>> sys.addaudithook(foo_event_hook)

   >>> with auditor.audit():
   ...     result = foo(1, 2, z=3)
   prehook called: args=(1, 2), kwargs={'z': 3}
   posthook called: result=6

Some of Seagrass's event hooks actually use runtime audit hooks internally. For
instance, ``seagrass.hooks.FileOpenHook`` keeps track of all calls to the
``open`` audit event that's built into Python in order to figure out what files
are opened during an event.

.. _PEP 578: https://www.python.org/dev/peps/pep-0578/
.. _Bypassing Python3.8 Audit Hooks: https://daddycocoaman.dev/posts/bypassing-python38-audit-hooks-part-1/

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
When are runtime audit hooks better than Seagrass?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- **Security:** if you're trying to audit a suspicious snippet of Python code,
  runtime audit hooks have the benefit that once they've been loaded with
  ``sys.addaudithook``, it's impossible (in theory) to remove them. Seagrass
  audit hooks don't come with the same guarantee.

- **Simplicity:** in some cases, it might just be easier to use runtime audit
  hooks, especially if you're trying to audit Python's `built-in audit events`_.
  For instance, if all you want to do is print which files are opened using
  ``open()`` within your code, you could do something like

  .. code:: python

     >>> from tempfile import NamedTemporaryFile

     >>> def file_open_hook(event, args):
     ...    if event == "open":
     ...        filename, mode, flags = args
     ...        print(f"{filename} opened with {mode=}, {flags=}")

     >>> sys.addaudithook(file_open_hook)

     >>> with open("/tmp/test.txt", "w") as f:
     ...     f.write("Hello, world!\n")
     /tmp/test.txt opened with mode='w', flags=524865


.. _built-in audit events: https://docs.python.org/3/library/audit_events.html
