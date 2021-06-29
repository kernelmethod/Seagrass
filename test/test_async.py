# Tests for creating events out of async functions

import unittest
from seagrass import get_current_event
from seagrass.hooks import CounterHook, LoggingHook
from test.utils import SeagrassTestCaseMixin, async_test


class AsyncEventTestCase(SeagrassTestCaseMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.ctr_hook = CounterHook()
        self.log_hook = LoggingHook(
            prehook_msg=lambda event, *args: f"Starting {event}",
            posthook_msg=lambda event, *args: f"Leaving {event}",
        )
        self.hooks = [self.ctr_hook]

    @async_test
    async def test_create_event_over_async_function(self):
        @self.auditor.audit("test.foo", use_async=True, hooks=self.hooks)
        async def foo():
            self.assertEqual(get_current_event(), "test.foo")

        with self.auditor.start_auditing():
            await foo()

        self.assertEqual(self.ctr_hook.event_counter["test.foo"], 1)


if __name__ == "__main__":
    unittest.main()
