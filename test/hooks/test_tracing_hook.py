import seagrass
import seagrass._typing as t
import unittest
from seagrass.base import ProtoHook, CleanupHook
from seagrass.hooks import TracingHook
from test.utils import HookTestCaseMixin
from types import FrameType


class EmptyTracingHook(TracingHook):
    """Example TracingHook where the tracing function does nothing."""

    def __init__(self) -> None:
        return super().__init__(self.tracefunc)

    def tracefunc(
        self, frame: FrameType, event: str, arg: t.Any
    ) -> t.Optional[TracingHook.TraceFunc]:
        return self.tracefunc


class LocalVariableExtractorHook(TracingHook):
    """Example TracingHook that extracts the value of MY_TEST_VARIABLE from the current frame's
    'locals' dictionary. The hook always stores the last value of MY_TEST_VARIABLE that it saw.
    """

    def __init__(self):
        super().__init__(self.tracefunc)
        self.reset()

    def tracefunc(
        self, frame: FrameType, event: str, arg: t.Any
    ) -> t.Optional[TracingHook.TraceFunc]:
        if "MY_TEST_VARIABLE" in frame.f_locals:
            self.last_event = self.current_event
            self.MY_TEST_VARIABLE = frame.f_locals["MY_TEST_VARIABLE"]
        return self.tracefunc

    def reset(self):
        self.last_event = None
        self.MY_TEST_VARIABLE = None


class TracingHookTestCase(HookTestCaseMixin, unittest.TestCase):

    check_interfaces = (CleanupHook,)

    @staticmethod
    def hook_gen():
        return LocalVariableExtractorHook()

    def test_hook_function(self):
        """Hook a function using a TracingHook."""

        @self.auditor.audit("event.foo", hooks=[self.hook])
        def foo(x):
            MY_TEST_VARIABLE = x
            self.logger.info(f"MY_TEST_VARIABLE={MY_TEST_VARIABLE}")

        @self.auditor.audit("event.bar", hooks=[self.hook])
        def bar():
            MY_TEST_VARIABLE = 1337
            self.logger.info(f"MY_TEST_VARIABLE={MY_TEST_VARIABLE}")

        with self.auditor.start_auditing(reset_hooks=True):
            foo(42)
            self.assertEqual(self.hook.MY_TEST_VARIABLE, 42)
            self.assertEqual(self.hook.last_event, "event.foo")

            bar()
            self.assertEqual(self.hook.MY_TEST_VARIABLE, 1337)
            self.assertEqual(self.hook.last_event, "event.bar")

            # Outside of events, the is_active property should be False
            self.assertEqual(self.hook.is_active, False)

    def test_nest_tracing_hook_events(self):
        """Nest multiple events using the same TracingHook."""

        # Create a test hook we'll use to perform tests after each event
        assertEqual = self.assertEqual
        trace_hook = self.hook

        class TestHook(ProtoHook[None]):
            def prehook(self, event, args, kwargs):
                if event == "event.foo":
                    assertEqual(trace_hook.MY_TEST_VARIABLE, 42 + 1)

            def posthook(self, event, result, context):
                if event == "event.foo":
                    assertEqual(trace_hook.MY_TEST_VARIABLE, 2 * (42 + 1))
                if event == "event.bar":
                    assertEqual(trace_hook.MY_TEST_VARIABLE, 2 * (42 + 1) - 5)

        test_hook = TestHook()

        @self.auditor.audit("event.foo", hooks=[trace_hook, test_hook])
        def foo(x):
            self.assertTrue(trace_hook.is_active)
            MY_TEST_VARIABLE = 2 * x
            return MY_TEST_VARIABLE

        @self.auditor.audit("event.bar", hooks=[trace_hook, test_hook])
        def bar(x):
            MY_TEST_VARIABLE = x + 1
            MY_TEST_VARIABLE = foo(MY_TEST_VARIABLE) - 5
            self.logger.info(f"MY_TEST_VARIABLE={MY_TEST_VARIABLE}")
            self.assertTrue(trace_hook.is_active)

        with self.auditor.start_auditing(reset_hooks=True):
            bar(42)

    def test_cannot_instantiate_more_than_one_tracing_hook(self):
        """The trace functions set by multiple TracingHooks can override one another. As such,
        an error should be raised whenever we try to active more than one TracingHook."""

        variable_hook = LocalVariableExtractorHook()
        empty_hook = EmptyTracingHook()

        # Of the three functions defined below, "foo" and "bar" should work fine, since only
        # one TracingHook is activated for each of them. "baz" should error out since it
        # causes both of the TracingHooks to be activated.
        @self.auditor.audit(seagrass.auto, hooks=[empty_hook])
        def foo():
            self.assertTrue(empty_hook.is_active)

        @self.auditor.audit(seagrass.auto, hooks=[variable_hook])
        def bar():
            self.assertTrue(variable_hook.is_active)

        @self.auditor.audit(seagrass.auto, hooks=[empty_hook, variable_hook])
        def baz():
            pass

        with self.auditor.start_auditing():
            foo()
            bar()
            with self.assertRaises(ValueError):
                baz()
            foo()
            bar()


if __name__ == "__main__":
    unittest.main()
