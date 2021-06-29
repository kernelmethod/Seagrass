import seagrass
import sys
import unittest
import warnings
from collections import Counter, defaultdict
from seagrass import auto, get_current_event
from seagrass.hooks import CounterHook
from test.utils import SeagrassTestCaseMixin, req_python_version

with seagrass.create_global_auditor() as _:

    class ExampleClass:
        # Test class used to check how functions are auto-named by Seagrass
        @staticmethod
        @seagrass.audit(auto)
        def say_hello(name: str) -> str:
            return f"Hello, {name}!"


class EventsTestCase(SeagrassTestCaseMixin, unittest.TestCase):
    """Tests for events created by Seagrass."""

    def test_wrap_class_property(self):
        # Override a class property to call a hook whenever it's accessed
        class Foo:
            def __init__(self):
                self.x = 0

            def add_one(self):
                return self.x + 1

        hook = CounterHook()

        @self.auditor.audit("test.foo.get_x", hooks=[hook])
        def get_x(self):
            return self.__x

        @self.auditor.audit("test.foo.set_x", hooks=[hook])
        def set_x(self, val):
            self.__x = val

        @self.auditor.audit("test.foo.del_x", hooks=[hook])
        def del_x(self):
            del self.__x

        setattr(Foo, "x", property(fget=get_x, fset=set_x, fdel=del_x))

        with self.auditor.start_auditing():
            f = Foo()
            f.x = 1
            y = f.x  # noqa: F841
            f.x += 2
            del f.x

        # We call get_x twice (once for y = f.x, another for f.x += 2)
        # We call set_x three times (once during Foo.__init__, once during f.x = 1, and
        #   once during f.x += 2)
        # We call del_x once (when we call del f.x)
        self.assertEqual(hook.event_counter["test.foo.get_x"], 2)
        self.assertEqual(hook.event_counter["test.foo.set_x"], 3)
        self.assertEqual(hook.event_counter["test.foo.del_x"], 1)

        # Now override the add_one function belonging to Foo
        current_add_one = Foo.add_one

        @self.auditor.audit("test.foo.add_one", hooks=[hook])
        def add_one(self, *args, **kwargs):
            return current_add_one(self, *args, **kwargs)

        setattr(Foo, "add_one", add_one)

        with self.auditor.start_auditing():
            f = Foo()
            result = f.add_one()

        self.assertEqual(result, 1)
        self.assertEqual(hook.event_counter["test.foo.add_one"], 1)

    def test_toggle_event(self):
        hook = CounterHook()

        @self.auditor.audit("test.foo", hooks=[hook])
        def foo():
            return

        @self.auditor.audit("test.bar", hooks=[hook])
        def bar():
            return foo()

        with self.auditor.start_auditing():
            bar()
            self.assertEqual(hook.event_counter["test.foo"], 1)
            self.assertEqual(hook.event_counter["test.bar"], 1)

            # After disabling an event, its event hooks should no longer be called
            self.auditor.toggle_event("test.foo", False)
            bar()
            self.assertEqual(hook.event_counter["test.foo"], 1)
            self.assertEqual(hook.event_counter["test.bar"], 2)

            # Now we re-enable the event so that hooks get called again
            self.auditor.toggle_event("test.foo", True)
            bar()
            self.assertEqual(hook.event_counter["test.foo"], 2)
            self.assertEqual(hook.event_counter["test.bar"], 3)

    @req_python_version(min=(3, 8))
    def test_wrap_function_and_create_sys_audit_event(self):
        # We should be able to set up sys.audit events when we wrap functions
        @self.auditor.audit("test.foo", raise_runtime_events=True)
        def foo(x, y, z=None):
            return x + y + (0 if z is None else z)

        @self.auditor.audit("test.bar", raise_runtime_events=False)
        def bar(x, y, z=None):
            return x + y + (0 if z is None else z)

        @self.auditor.audit(
            "test.baz",
            raise_runtime_events=True,
            prehook_audit_event_name="baz_prehook",
            posthook_audit_event_name="baz_posthook",
        )
        def baz(x, y, z=None):
            return x + y + (0 if z is None else z)

        events_counter = Counter()
        args_dict = defaultdict(list)

        def audit_hook(event: str, *args):
            try:
                if event.startswith("prehook:") or event.startswith("posthook:"):
                    events_counter[event] += 1
                    args_dict[event].append(args)
                elif event in ("baz_prehook", "baz_posthook"):
                    events_counter[event] += 1
                    args_dict[event].append(args)
            except Exception as ex:
                warnings.warn(f"Exception raised in audit_hook: ex={ex}")

        sys.addaudithook(audit_hook)

        test_args = [(-3, 4), (5, 8), (0, 0)]
        test_kwargs = [{}, {}, {"z": 1}]

        def run_fns(args_list, kwargs_list):
            for (args, kwargs) in zip(args_list, kwargs_list):
                for fn in (foo, bar, baz):
                    fn(*args, **kwargs)

        # The following call to run_fns shouldn't raise any audit events since
        # it isn't performed in an auditing context.
        run_fns(test_args, test_kwargs)
        self.assertEqual(set(events_counter), set())
        self.assertEqual(set(args_dict), set())

        # Now some audit events should be raised:
        with self.auditor.start_auditing():
            run_fns(test_args, test_kwargs)

        expected_prehooks = ["prehook:test.foo", "baz_prehook"]
        expected_posthooks = ["posthook:test.foo", "baz_posthook"]
        self.assertEqual(
            set(events_counter), set(expected_prehooks + expected_posthooks)
        )
        self.assertEqual(set(events_counter), set(args_dict))

        for event in expected_prehooks:
            self.assertEqual(events_counter[event], len(test_args))
            args = [args[0][0] for args in args_dict[event]]
            kwargs = [args[0][1] for args in args_dict[event]]
            self.assertEqual(args, test_args)
            self.assertEqual(kwargs, test_kwargs)

        # If we try running our functions outside of an auditing context again,
        # we should once again find that no system events are raised.
        events_counter.clear()
        args_dict.clear()
        run_fns(test_args, test_kwargs)
        self.assertEqual(set(events_counter), set())
        self.assertEqual(set(args_dict), set())

    @req_python_version(max=(3, 8))
    def test_get_error_with_runtime_events_for_python_before_38(self):
        """For Python versions before 3.8, sys.audit and sys.addaudithook do not exist, so
        an exception should be raised if raise_runtime_events=True."""
        with self.assertRaises(NotImplementedError):
            self.auditor.create_event("my_test_event", raise_runtime_events=True)

    def test_auto_name_event(self):
        from pathlib import Path

        auhome = self.auditor.audit(auto, Path.home)
        self.assertEqual(auhome.__event_name__, "pathlib.Path.home")

        # Check the name of the audited function from the ExampleClass class at
        # the top of the file.
        self.assertEqual(
            ExampleClass.say_hello.__event_name__, f"{__name__}.ExampleClass.say_hello"
        )

    def test_get_current_event(self):
        @self.auditor.audit("test.foo")
        def foo():
            self.assertEqual(get_current_event(), "test.foo")

        @self.auditor.audit("test.bar")
        def bar():
            self.assertEqual(get_current_event(), "test.bar")
            foo()
            self.assertEqual(get_current_event(), "test.bar")

        with self.auditor.start_auditing():
            foo()
            bar()

        # We should be able to specify a default value for get_current_event(). If no default is
        # specified and an event isn't being executed, an exception should be thrown.
        self.assertEqual(get_current_event(None), None)
        with self.assertRaises(LookupError):
            get_current_event()


if __name__ == "__main__":
    unittest.main()
