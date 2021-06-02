# Tests for raising Python audit events with sys.audit through Auditors

import sys
import unittest
import warnings
from collections import Counter, defaultdict
from seagrass import Auditor
from seagrass.hooks import CounterHook


class EventsTestCase(unittest.TestCase):
    """Tests for events created by Seagrass."""

    def setUp(self):
        self.auditor = Auditor()

    def test_toggle_event(self):
        hook = CounterHook()

        @self.auditor.decorate("test.foo", hooks=[hook])
        def foo():
            return

        @self.auditor.decorate("test.bar", hooks=[hook])
        def bar():
            return foo()

        with self.auditor.audit():
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


class SysAuditEventsTestCase(unittest.TestCase):
    """We should be able to set up sys.audit events when we wrap functions."""

    def setUp(self):
        self.auditor = Auditor()

    def test_wrap_function_and_create_sys_audit_event(self):
        @self.auditor.decorate("test.foo", raise_audit_event=True)
        def foo(x, y, z=None):
            return x + y + (0 if z is None else z)

        @self.auditor.decorate("test.bar", raise_audit_event=False)
        def bar(x, y, z=None):
            return x + y + (0 if z is None else z)

        @self.auditor.decorate(
            "test.baz",
            raise_audit_event=True,
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
                warnings.warn(f"Exception raised in audit_hook: {ex=}")

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
        with self.auditor.audit():
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


if __name__ == "__main__":
    unittest.main()
