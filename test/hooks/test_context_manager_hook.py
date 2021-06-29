import unittest
from collections import Counter
from seagrass import get_current_event, get_audit_logger
from seagrass.base import CleanupHook
from seagrass.hooks import ContextManagerHook
from test.utils import HookTestCaseMixin


class CounterContextManager:
    def __init__(self):
        self.ctr = Counter()
        self.exc_ctr = Counter()

    def __enter__(self):
        self.ctr[get_current_event()] += 1

    def __exit__(self, exc_type, exc_val, traceback):
        if exc_type is not None:
            self.exc_ctr[get_current_event()] += 1


class LoggerContextManager:
    def __enter__(self):
        get_audit_logger().debug(f"Calling {get_current_event()}")

    def __exit__(self, exc_type, exc_val, traceback):
        get_audit_logger().debug(f"Exiting {get_current_event()}")


class ContextManagerHookTestCase(HookTestCaseMixin, unittest.TestCase):

    check_interfaces = (CleanupHook,)

    def setUp(self):
        super().setUp()
        self.cm = CounterContextManager()
        self.hook = ContextManagerHook(self.cm, nest=True)

    def test_hook_function(self):
        @self.auditor.audit("test.foo", hooks=[self.hook])
        def foo():
            pass

        @self.auditor.audit("test.bar", hooks=[self.hook])
        def bar():
            assert False

        with self.auditor.start_auditing():
            foo()
            with self.assertRaises(AssertionError):
                bar()

        self.assertEqual(self.cm.ctr["test.foo"], 1)
        self.assertEqual(self.cm.ctr["test.bar"], 1)
        self.assertEqual(self.cm.exc_ctr["test.foo"], 0)
        self.assertEqual(self.cm.exc_ctr["test.bar"], 1)


class CallableContextManagerHookTestCase(HookTestCaseMixin, unittest.TestCase):
    """Tests for ContextManagerHook in the case where the input context manager is a callable
    function."""

    check_interfaces = (CleanupHook,)

    @staticmethod
    def hook_gen():
        return ContextManagerHook(LoggerContextManager, nest=False)

    def test_hook_function(self):
        @self.auditor.audit("test.foo", hooks=[self.hook])
        def foo():
            pass

        @self.auditor.audit("test.bar", hooks=[self.hook])
        def bar():
            foo()

        with self.auditor.start_auditing():
            bar()

        output = self.logging_output.getvalue().rstrip().split("\n")
        self.assertEqual(output[0], "(DEBUG) Calling test.bar")
        self.assertEqual(output[1], "(DEBUG) Exiting test.bar")

        self.hook.nest = True

        with self.auditor.start_auditing():
            bar()

        output = self.logging_output.getvalue().rstrip().split("\n")
        output = output[2:]
        self.assertEqual(output[0], "(DEBUG) Calling test.bar")
        self.assertEqual(output[1], "(DEBUG) Calling test.foo")
        self.assertEqual(output[2], "(DEBUG) Exiting test.foo")
        self.assertEqual(output[3], "(DEBUG) Exiting test.bar")


if __name__ == "__main__":
    unittest.main()
