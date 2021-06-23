import typing as t
import unittest
from seagrass.base import CleanupHook
from seagrass.hooks import TracingHook
from test.utils import HookTestCaseMixin
from types import FrameType


class EmptyTracingHook(TracingHook):
    """Example TracingHook where the tracing function does nothing."""

    def tracefunc(
        self, frame: FrameType, event: str, arg: t.Any
    ) -> TracingHook.TraceFunc:
        return self.tracefunc


class LocalVariableExtractorHook(TracingHook):
    """Example TracingHook that extracts the value of MY_TEST_VARIABLE from the current frame's
    'locals' dictionary. The hook always stores the last value of MY_TEST_VARIABLE that it saw.
    """

    def __init__(self):
        super().__init__()
        self.reset()

    def tracefunc(
        self, frame: FrameType, event: str, arg: t.Any
    ) -> TracingHook.TraceFunc:
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
            self.logger.info(f"{MY_TEST_VARIABLE=}")

        @self.auditor.audit("event.bar", hooks=[self.hook])
        def bar():
            MY_TEST_VARIABLE = 1337
            self.logger.info(f"{MY_TEST_VARIABLE=}")

        with self.hook:
            with self.auditor.start_auditing(reset_hooks=True):
                foo(42)
                self.assertEqual(self.hook.MY_TEST_VARIABLE, 42)
                self.assertEqual(self.hook.last_event, "event.foo")

                bar()
                self.assertEqual(self.hook.MY_TEST_VARIABLE, 1337)
                self.assertEqual(self.hook.last_event, "event.bar")

                # Outside of events, the is_active property should be False
                self.assertEqual(self.hook.is_active, False)

    def test_cannot_instantiate_more_than_one_tracing_hook(self):
        """The trace functions set by multiple TracingHooks can override one another. As such,
        error to try to make more than one TracingHook the current global TracingHook."""

        empty_hook = EmptyTracingHook()

        with empty_hook:
            with self.assertRaises(ValueError):
                with EmptyTracingHook() as _:
                    pass
            with self.assertRaises(ValueError):
                with LocalVariableExtractorHook() as _:
                    pass

            # It isn't an error to create a new hook...
            new_hook = EmptyTracingHook()

            # ... but it _is_ an error to try and make it the active hook
            with self.assertRaises(ValueError):
                new_hook.set_trace()

        # Once we've left the exterior context, it should be possible to make new hooks the
        # current TracingHook again
        self.hook.set_trace()
        with self.assertRaises(ValueError):
            empty_hook.set_trace()

        # Shouldn't get any errors
        empty_hook.remove_trace()
        self.hook.remove_trace()
        empty_hook.set_trace()
        empty_hook.remove_trace()


if __name__ == "__main__":
    unittest.main()
