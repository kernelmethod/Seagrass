# Tests for Auditor creation and basic functionality

import logging
import unittest
from io import StringIO
from seagrass import Auditor
from seagrass.errors import EventNotFoundError
from test.base import SeagrassTestCaseBase


class CreateAuditorTestCase(unittest.TestCase):
    """Tests for creating a new Auditor instance."""

    def test_create_auditor_with_logger(self):
        # Create a new Auditor with a custom logger
        self.logging_output = StringIO()

        self.logger_name = "seagrass.test"
        self.logger = logging.getLogger(self.logger_name)
        self.logger.setLevel(logging.DEBUG)
        fh = logging.StreamHandler(self.logging_output)
        fh.setLevel(logging.INFO)

        formatter = logging.Formatter("%(message)s")
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)

        auditor = Auditor(logger=self.logger)
        auditor.logger.info("Hello, world!")
        auditor.logger.debug("This message shouldn't appear")

        self.logging_output.seek(0)
        lines = self.logging_output.readlines()
        self.assertEqual(lines, ["Hello, world!\n"])


class SimpleAuditorFunctionsTestCase(SeagrassTestCaseBase):
    def test_define_new_event(self):
        # Define a new event and ensure that it gets added to the auditor's events
        # dictionary and event_wrapper dictionary
        @self.auditor.decorate("test.foo")
        def foo():
            return

        self.assertIn("test.foo", self.auditor.events)
        self.assertIn("test.foo", self.auditor.event_wrappers)

    def test_define_two_events_with_the_same_name(self):
        @self.auditor.decorate("test.foo")
        def foo_1():
            return

        with self.assertRaises(ValueError):

            @self.auditor.decorate("test.foo")
            def foo_2():
                return

    def test_create_empty_event(self):
        # Create a new audit event that doesn't wrap any existing function.
        with self.assertRaises(EventNotFoundError):
            self.auditor.raise_event("test.signal", 1, 2, name="Alice")

        class TestHook:
            def __init__(self):
                self.reset()

            def prehook(self, event_name, args, kwargs):
                self.last_prehook_args = (event_name, args, kwargs)

            def posthook(self, event_name, result, context):
                self.last_posthook_args = (event_name, result)

            def reset(self):
                self.last_prehook_args = self.last_posthook_args = None

        hook = TestHook()
        self.auditor.create_event("test.signal", hooks=[hook])

        # Event shouldn't be triggered outside of an auditing context
        self.auditor.raise_event("test.signal", 1, 2, name="Alice")
        self.assertEqual(hook.last_prehook_args, None)
        self.assertEqual(hook.last_posthook_args, None)

        with self.auditor.audit():
            self.auditor.raise_event("test.signal", 1, 2, name="Alice")

        self.assertEqual(
            hook.last_prehook_args, ("test.signal", (1, 2), {"name": "Alice"})
        )
        self.assertEqual(hook.last_posthook_args, ("test.signal", None))

    def test_raise_event_cumsum(self):
        # Insert an audit event into the function my_sum so that we can monitor the internal
        # state of the function as it's executing. In this case, we'll be retrieving the
        # cumulative sum at various points in time.
        def my_sum(*args):
            total = 0.0
            for arg in args:
                self.auditor.raise_event("my_sum.cumsum", total)
                total += arg

        class MySumHook:
            def __init__(self):
                self.reset()

            def prehook(self, event_name, args, kwargs):
                self.cumsums.append(args[0])

            def posthook(self, *args):
                pass

            def reset(self):
                self.cumsums = []

        hook = MySumHook()
        self.auditor.create_event("my_sum.cumsum", hooks=[hook])

        with self.auditor.audit():
            my_sum(1, 2, 3, 4)

        self.assertEqual(hook.cumsums, [0.0, 1.0, 3.0, 6.0])


if __name__ == "__main__":
    unittest.main()
