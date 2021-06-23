# Tests for Auditor creation and basic functionality

import logging
import seagrass
import unittest
from io import StringIO
from seagrass import Auditor, get_audit_logger
from seagrass.errors import EventNotFoundError
from test.utils import SeagrassTestCaseMixin


class CreateAuditorTestCase(unittest.TestCase):
    """Tests for creating a new Auditor instance."""

    def _clear_logging_output(self):
        # Helper function to clear output buffer used for testing logging
        self.logging_output.seek(0)
        self.logging_output.truncate()

    def _configure_logger(self, logger: logging.Logger):
        # Set the testing configuration for an input logger
        logger.setLevel(logging.INFO)

        fh = logging.StreamHandler(self.logging_output)
        fh.setLevel(logging.DEBUG)

        formatter = logging.Formatter("(%(levelname)s) %(name)s: %(message)s")
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    def setUp(self):
        self.logging_output = StringIO()

    def test_default_logger_used_by_auditor(self):
        # By default, Auditor should use the "seagrass" logger if no logger is specified
        self._configure_logger(logging.getLogger("seagrass"))

        auditor = Auditor()
        auditor.logger.info("Hello, world!")
        auditor.logger.debug("This message shouldn't appear")

        output = self.logging_output.getvalue()
        self.assertEqual(output, "(INFO) seagrass: Hello, world!\n")

    def test_use_custom_logger_for_auditor(self):
        # If a logger is explicitly specified, Auditor should use that logger instead
        # of the default. The logger can either be provided as a logging.Logger
        # instance or as the name of a logger.
        self._configure_logger(logging.getLogger("test_logger"))

        for logger in ("test_logger", logging.getLogger("test_logger")):
            auditor = Auditor(logger=logger)
            auditor.logger.info("Hello, world!")
            auditor.logger.debug("This message shouldn't appear")

            output = self.logging_output.getvalue()
            self.assertEqual(output, "(INFO) test_logger: Hello, world!\n")

            self._clear_logging_output()


class SimpleAuditorFunctionsTestCase(SeagrassTestCaseMixin, unittest.TestCase):
    def test_define_new_event(self):
        # Define a new event and ensure that it gets added to the auditor's events
        # dictionary and event_wrapper dictionary
        @self.auditor.audit("test.foo")
        def foo():
            return

        self.assertIn("test.foo", self.auditor.events)
        self.assertIn("test.foo", self.auditor.event_wrappers)

    def test_define_two_events_with_the_same_name(self):
        @self.auditor.audit("test.foo")
        def foo_1():
            return

        with self.assertRaises(ValueError):

            @self.auditor.audit("test.foo")
            def foo_2():
                return

    def test_create_empty_event(self):
        # Create a new audit event that doesn't wrap any existing function.
        with self.assertRaises(EventNotFoundError):
            self.auditor.raise_event("test.signal", 1, 2, name="Alice")

        class TestHook:
            def __init__(self):
                self.last_prehook_args = self.last_posthook_args = None

            def prehook(self, event_name, args, kwargs):
                self.last_prehook_args = (event_name, args, kwargs)

            def posthook(self, event_name, result, context):
                self.last_posthook_args = (event_name, result)

        hook = TestHook()
        self.auditor.create_event("test.signal", hooks=[hook])

        # Event shouldn't be triggered outside of an auditing context
        self.auditor.raise_event("test.signal", 1, 2, name="Alice")
        self.assertEqual(hook.last_prehook_args, None)
        self.assertEqual(hook.last_posthook_args, None)

        with self.auditor.start_auditing():
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
                self.cumsums = []

            def prehook(self, event_name, args, kwargs):
                self.cumsums.append(args[0])

            def posthook(self, *args):
                pass

        hook = MySumHook()
        self.auditor.create_event("my_sum.cumsum", hooks=[hook])

        with self.auditor.start_auditing():
            my_sum(1, 2, 3, 4)

        self.assertEqual(hook.cumsums, [0.0, 1.0, 3.0, 6.0])

    def test_get_audit_logger(self):
        # Tests for the get_audit_logger function

        outer_auditor = Auditor(logger="outer")
        inner_auditor = Auditor(logger="inner")
        self.assertNotEqual(outer_auditor.logger, inner_auditor.logger)

        # Outside of an auditing context, get_audit_logger should return None
        self.assertEqual(get_audit_logger(), None)

        # Within an auditing context, get_audit_logger() should return the logger
        # for the most recent auditing context.
        with outer_auditor.start_auditing():
            self.assertEqual(get_audit_logger(), outer_auditor.logger)

            with inner_auditor.start_auditing():
                self.assertEqual(get_audit_logger(), inner_auditor.logger)

            self.assertEqual(get_audit_logger(), outer_auditor.logger)

        # Now that we're back outside of an auditing context, get_audit_logger()
        # should once again return None.
        self.assertEqual(get_audit_logger(), None)

    def test_filter_events(self):
        hook = seagrass.hooks.CounterHook()
        self.auditor.create_event("test.foo", hooks=[hook])
        self.auditor.create_event("bar", hooks=[hook])

        ec = hook.event_counter

        def raise_events():
            for event in ("test.foo", "bar"):
                self.auditor.raise_event(event)

        with self.auditor.start_auditing(
            filter=lambda event: event.startswith("test"), reset_hooks=True
        ):
            raise_events()
            self.assertEqual(ec["test.foo"], 1)
            self.assertEqual(ec["bar"], 0)

        # After we leave the auditing context, the filter should be reset.
        with self.auditor.start_auditing(reset_hooks=True):
            raise_events()
            self.assertEqual(ec["test.foo"], 1)
            self.assertEqual(ec["bar"], 1)

        # It should also be possible to modify the event filter using the setter. This setter is not
        # context-dependent.
        self.auditor.event_filter = lambda event: event.startswith("test")

        with self.auditor.start_auditing(reset_hooks=True):
            raise_events()
            self.assertEqual(ec["test.foo"], 1)
            self.assertEqual(ec["bar"], 0)

        with self.auditor.start_auditing(reset_hooks=True):
            raise_events()
            self.assertEqual(ec["test.foo"], 1)
            self.assertEqual(ec["bar"], 0)

        # However, once we call reset_filter, all events should start executing as normal again
        self.auditor.reset_filter()
        with self.auditor.start_auditing(reset_hooks=True):
            raise_events()
            self.assertEqual(ec["test.foo"], 1)
            self.assertEqual(ec["bar"], 1)


class GlobalAuditorTestCase(unittest.TestCase):
    """Tests for using the global auditor instance."""

    def test_use_counter_hook_with_global_auditor(self):
        hook = seagrass.hooks.CounterHook()

        @seagrass.audit("test.foo", hooks=[hook])
        def foo():
            pass

        with seagrass.start_auditing():
            for _ in range(10):
                foo()

        self.assertEqual(hook.event_counter["test.foo"], 10)

    def test_create_global_auditor_in_context(self):
        hook = seagrass.hooks.CounterHook()

        with seagrass.create_global_auditor() as auditor:
            self.assertEqual(seagrass.global_auditor(), auditor)

            # Any events created inside of this context should be created with the new auditor
            @seagrass.audit("test.foo", hooks=[hook])
            def foo():
                pass

        # Outside of the context, the auditor should be set back to the original
        # global auditor.
        self.assertNotEqual(seagrass.global_auditor(), auditor)

        # Events created inside of the context should only be raised with the newly-created
        # auditor.
        with seagrass.start_auditing(reset_hooks=True):
            foo()
            self.assertEqual(hook.event_counter["test.foo"], 0)

        with auditor.start_auditing(reset_hooks=True):
            foo()
            self.assertEqual(hook.event_counter["test.foo"], 1)

        # It should also be possible to create an Auditor and pass it into create_global_auditor
        auditor = Auditor()
        with seagrass.create_global_auditor(auditor):
            self.assertEqual(seagrass.global_auditor(), auditor)


if __name__ == "__main__":
    unittest.main()
