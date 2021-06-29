# Tests for creating events out of async functions

import asyncio
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
        self.hooks = [self.ctr_hook, self.log_hook]

    @async_test
    async def test_create_event_over_async_function(self):
        """Ensure that auditing works correctly when we call an async event."""

        @self.auditor.audit("test.foo", use_async=True, hooks=self.hooks)
        async def foo():
            self.assertEqual(get_current_event(), "test.foo")

        with self.auditor.start_auditing():
            await foo()

        self.assertEqual(self.ctr_hook.event_counter["test.foo"], 1)

        output = self.logging_output.getvalue().rstrip().split("\n")
        self.assertEqual(output[0], "(DEBUG) Starting test.foo")
        self.assertEqual(output[1], "(DEBUG) Leaving test.foo")

    @async_test
    async def test_wrap_nested_async_events(self):
        """Ensure that auditing works correctly when we call an async event inside another
        async event."""

        @self.auditor.async_audit("test.foo", hooks=self.hooks)
        async def foo():
            self.assertEqual(get_current_event(), "test.foo")

        @self.auditor.async_audit("test.bar", hooks=self.hooks)
        async def bar(recurse: bool):
            self.assertEqual(get_current_event(), "test.bar")
            await foo()
            self.assertEqual(get_current_event(), "test.bar")

            if recurse:
                await asyncio.gather(bar(False), foo(), bar(False))

            self.assertEqual(get_current_event(), "test.bar")

        with self.auditor.start_auditing():
            await bar(True)

        self.assertEqual(self.ctr_hook.event_counter["test.foo"], 4)
        self.assertEqual(self.ctr_hook.event_counter["test.bar"], 3)

    @async_test
    async def test_wrapped_async_and_sync_events(self):
        """Check that auditing works correctly if we run a sync event inside an async event."""

        @self.auditor.audit("test.foo", hooks=self.hooks)
        def foo():
            self.assertEqual(get_current_event(), "test.foo")

        @self.auditor.async_audit("test.bar", hooks=self.hooks)
        async def bar(recurse: bool):
            self.assertEqual(get_current_event(), "test.bar")
            foo()
            self.assertEqual(get_current_event(), "test.bar")

            if recurse:
                await bar(False)
                foo()
                await bar(False)

            self.assertEqual(get_current_event(), "test.bar")

        with self.auditor.start_auditing():
            await bar(True)

        self.assertEqual(self.ctr_hook.event_counter["test.foo"], 4)
        self.assertEqual(self.ctr_hook.event_counter["test.bar"], 3)


if __name__ == "__main__":
    unittest.main()
