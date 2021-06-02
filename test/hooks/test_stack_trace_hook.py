import unittest
from seagrass import Auditor
from seagrass.hooks import StackTraceHook


class StackTraceHookTestCase(unittest.TestCase):
    """Tests for the StackTraceHook auditing hook."""

    def test_hook_function(self):
        auditor = Auditor()
        hook = StackTraceHook()

        @auditor.decorate("test.foo", hooks=[hook])
        def foo():
            return

        @auditor.decorate("test.bar", hooks=[hook])
        def bar():
            return foo()

        with auditor.audit():
            foo()
            bar()

        # There are two unique stack traces for where test.foo gets
        # called, but only one for test.bar.
        self.assertEqual(len(hook.stack_trace_counter["test.foo"]), 2)
        self.assertEqual(len(hook.stack_trace_counter["test.bar"]), 1)

        hook.reset()
        self.assertEqual(len(hook.stack_trace_counter["test.foo"]), 0)
        self.assertEqual(len(hook.stack_trace_counter["test.bar"]), 0)


if __name__ == "__main__":
    unittest.main()
