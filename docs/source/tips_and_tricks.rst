.. _tips-and-tricks:

===============
Tips and tricks
===============

-------------------------
Auditing class attributes
-------------------------

Suppose we have a module ``example`` that defines the following class for
representing a point in a two-dimensional space:

.. testcode:: wrapping-class-attributes

   # example/__init__.py
   import math

   class Point2D:

       def __init__(self, x, y):
           self.x = x
           self.y = y

       def norm(self):
           return math.sqrt(self.x**2 + self.y**2)

       @property
       def tuple(self):
           return (self.x, self.y)

It's fairly straightforward to audit methods of this class, like ``norm``. We
simply create a new method using ``auditor.wrap``, then replace the old method
with the new one:

.. doctest:: wrapping-class-attributes

   >>> from example import Point2D  # doctest: +SKIP

   >>> from seagrass import Auditor

   >>> auditor = Auditor()

   >>> class PrintEventHook:
   ...     def prehook(self, event, args, kwargs):
   ...         print(f"{self.__class__.__name__}: {event} triggered")
   ...     def posthook(self, event, result, context):
   ...         pass
   ...     def reset(self):
   ...         pass

   >>> hooks = [PrintEventHook()]

   >>> aunorm = auditor.wrap(Point2D.norm, "event.norm", hooks=hooks)

   >>> Point2D.norm = aunorm

   >>> with auditor.audit():
   ...     p = Point2D(3, 4)
   ...     print(f"{p.norm()=}")
   PrintEventHook: event.norm triggered
   p.norm()=5.0

   >>> auditor.toggle_event("event.norm", False)

However, what if we want to audit a class member that isn't a method? For
instance, maybe we want to know in what parts of the code the attribute ``x``
gets accessed or modified. A little trick we can use for this is to redefine
``x`` as being a ``property`` of the class ``Point2D``, and then wrap the
getter, setter, and deleter methods for that property.

.. doctest:: wrapping-class-attributes

   >>> getter_hooks = setter_hooks = deleter_hooks = [PrintEventHook()]

   >>> @auditor.decorate("point2d.get_x", hooks=getter_hooks)
   ... def get_x(self):
   ...     return self.__x

   >>> @auditor.decorate("point2d.set_x", hooks=setter_hooks)
   ... def set_x(self, val):
   ...     self.__x = val

   >>> @auditor.decorate("point2d.del_x", hooks=deleter_hooks)
   ... def del_x(self):
   ...     del self.__x

   >>> setattr(Point2D, "x", property(fget=get_x, fset=set_x, fdel=del_x))

   >>> auditor.toggle_auditing(True)

   >>> p = Point2D(3, 4)
   PrintEventHook: point2d.set_x triggered

   >>> p.norm()
   PrintEventHook: point2d.get_x triggered
   5.0

   >>> p.x += 1
   PrintEventHook: point2d.get_x triggered
   PrintEventHook: point2d.set_x triggered

   >>> auditor.toggle_auditing(False)

   >>> for func in ("get_x", "set_x", "del_x"):
   ...     auditor.toggle_event(f"point2d.{func}", False)

Finally, what if we want to audit an attribute that's already a property, like
``tuple``? In that case, we just need to create a new property that wraps the
getter, setter, and/or deleter methods of the old property.
[#overriding-property-attributes]_

.. doctest:: wrapping-class-attributes

   >>> isinstance(Point2D.tuple, property)
   True

   >>> aufget = auditor.wrap(Point2D.tuple.fget, "tuple_getter", hooks=hooks)

   >>> new_prop = property(
   ...     fget=aufget, fset=Point2D.tuple.fset, fdel=Point2D.tuple.fdel,
   ... )

   >>> setattr(Point2D, "tuple", new_prop)

   >>> with auditor.audit():
   ...     p = Point2D(3, 4)
   ...     print(p.tuple)
   PrintEventHook: tuple_getter triggered
   (3, 4)

.. rubric:: Footnotes

.. [#overriding-property-attributes]

   It's tempting to try directly overriding the attributes of the original
   property by redefining ``Point2D.tuple.fget``. However, ``fget`` is a
   read-only attribute of a property like ``Point2D.tuple``, and you will get an
   ``AttributeError`` if you try to do this:

   .. testsetup::

      from seagrass import Auditor

      class Point2D:
          # Omit most of class definition; only really need this part
          @property
          def tuple(self):
              return tuple()

      auditor = Auditor()
      hooks = []

   .. doctest::

      >>> aufget = auditor.wrap(Point2D.tuple.fget, "tuple_getter", hooks=hooks)

      >>> setattr(Point2D.tuple, "fget", aufget) # doctest: +IGNORE_EXCEPTION_DETAIL
      Traceback (most recent call last):
      AttributeError: readonly attribute

   As a result, we have to take the more indirect route of defining a new
   property that uses the wrapped getter method, and then override the original
   ``tuple`` property with the new one.