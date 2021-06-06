# Tests for the CounterHook auditing hook.

from seagrass import Auditor
from seagrass.hooks import CounterHook
import unittest


class CounterHookTestCase(unittest.TestCase):
    def test_hook_function(self):
        auditor = Auditor()
        hook = CounterHook()

        @auditor.decorate("test.say_hello", hooks=[hook])
        def say_hello(name: str) -> str:
            return f"Hello, {name}!"

        self.assertEqual(hook.event_counter["test.say_hello"], 0)

        # Hook should not get called outside of an auditing context
        say_hello("Alice")
        self.assertEqual(hook.event_counter["test.say_hello"], 0)

        with auditor.audit():
            for name in ("Alice", "Bob", "Cathy"):
                say_hello(name)
        self.assertEqual(hook.event_counter["test.say_hello"], 3)
        self.assertEqual(set(hook.event_counter), set(("test.say_hello",)))

        # Upon resetting the hook, all event counts should be set back to zero
        hook.reset()
        self.assertEqual(hook.event_counter["test.say_hello"], 0)


if __name__ == "__main__":
    unittest.main()
