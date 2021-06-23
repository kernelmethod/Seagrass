# Tests for the CounterHook auditing hook.

from seagrass.base import ResettableHook, LogResultsHook
from seagrass.hooks import CounterHook
from test.utils import HookTestCaseMixin
import unittest


class CounterHookTestCase(HookTestCaseMixin, unittest.TestCase):

    hook_gen = CounterHook
    check_interfaces = (ResettableHook, LogResultsHook)

    def test_hook_function(self):
        @self.auditor.audit("test.say_hello", hooks=[self.hook])
        def say_hello(name: str) -> str:
            return f"Hello, {name}!"

        self.assertEqual(self.hook.event_counter["test.say_hello"], 0)

        # Hook should not get called outside of an auditing context
        say_hello("Alice")
        self.assertEqual(self.hook.event_counter["test.say_hello"], 0)

        with self.auditor.start_auditing():
            for name in ("Alice", "Bob", "Cathy"):
                say_hello(name)
        self.assertEqual(self.hook.event_counter["test.say_hello"], 3)
        self.assertEqual(set(self.hook.event_counter), set(("test.say_hello",)))

        # Upon resetting the hook, all event counts should be set back to zero
        self.hook.reset()
        self.assertEqual(self.hook.event_counter["test.say_hello"], 0)

    def test_counter_hook_logging(self):
        # Collect event information with CounterHook and then check the logs
        # that are emitted by CounterHook.log_results.

        self.auditor.create_event("event_b", hooks=[self.hook])
        self.auditor.create_event("event_a", hooks=[self.hook])
        self.auditor.create_event("event_c", hooks=[self.hook])

        with self.auditor.start_auditing(log_results=True):
            for _ in range(904):
                self.auditor.raise_event("event_b")
            for _ in range(441):
                self.auditor.raise_event("event_a")
            for _ in range(58):
                self.auditor.raise_event("event_c")

        lines = self.logging_output.getvalue().rstrip().split("\n")
        self.assertEqual(len(lines), 4)
        self.assertEqual(lines[0], "(INFO) Calls to events recorded by CounterHook:")
        self.assertEqual(lines[1], "(INFO)     event_a: 441")
        self.assertEqual(lines[2], "(INFO)     event_b: 904")
        self.assertEqual(lines[3], "(INFO)     event_c: 58")

    def test_disable_counter_hook(self):
        self.auditor.create_event("my_event", hooks=[self.hook])

        with self.auditor.start_auditing(reset_hooks=True):
            self.auditor.raise_event("my_event")
            self.assertEqual(self.hook.event_counter["my_event"], 1)

        self.hook.enabled = False

        with self.auditor.start_auditing(reset_hooks=True):
            self.auditor.raise_event("my_event")
            self.assertEqual(self.hook.event_counter["my_event"], 0)


if __name__ == "__main__":
    unittest.main()
