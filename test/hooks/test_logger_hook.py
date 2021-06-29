# Tests for the LoggerHook auditing hook.

import logging
import unittest
from functools import reduce
from operator import add, mul
from seagrass.hooks import LoggingHook
from test.utils import HookTestCaseMixin, SeagrassTestCaseMixin


class LoggingHookTestCase(HookTestCaseMixin, unittest.TestCase):
    def setUp(self):
        super(HookTestCaseMixin, self).setUp()

        self.hook_pre = LoggingHook(
            prehook_msg=lambda e, args, kwargs: f"hook_pre: {e}, args={args}, kwargs={kwargs}",
        )
        self.hook_both = LoggingHook(
            prehook_msg=lambda e, args, kwargs: f"hook_both: {e}, args={args}, kwargs={kwargs}",
            posthook_msg=lambda e, result: f"hook_both: {e}, result={result}",
            loglevel=logging.INFO,
        )

        # Use hook_both as self.hook for running additional tests that are defined for
        # test case classes that subclass from HookTestMixin.
        self.hook = self.hook_both

    def test_hook_function(self):
        event = "test.multiply_or_add"

        @self.auditor.audit(event, hooks=[self.hook_pre, self.hook_both])
        def multiply_or_add(*args, op="*"):
            if op == "*":
                return reduce(mul, args, 1)
            elif op == "+":
                return reduce(add, args, 0)
            else:
                raise ValueError(f"Unknown operation '{op}'")

        args = (1, 2, 3, 4)
        kwargs_add = {"op": "+"}
        with self.auditor.start_auditing():
            multiply_or_add(*args)
            multiply_or_add(*args, **kwargs_add)

        output = self.logging_output.getvalue().rstrip().split("\n")
        self.assertEqual(
            output[0], f"(DEBUG) hook_pre: {event}, args={args}, kwargs={{}}"
        )
        self.assertEqual(
            output[1], f"(INFO) hook_both: {event}, args={args}, kwargs={{}}"
        )
        self.assertEqual(output[2], f"(INFO) hook_both: {event}, result={24}")
        self.assertEqual(
            output[3], f"(DEBUG) hook_pre: {event}, args={args}, kwargs={kwargs_add}"
        )
        self.assertEqual(
            output[4], f"(INFO) hook_both: {event}, args={args}, kwargs={kwargs_add}"
        )
        self.assertEqual(output[5], f"(INFO) hook_both: {event}, result={10}")


class MiscellaneousLoggingHookTestCase(SeagrassTestCaseMixin, unittest.TestCase):
    def test_raise_error_if_neither_message_is_specified(self):
        """A ValueError should be raised if we try to create a LoggingHook without providing both
        a prehook_msg and a posthook_msg."""
        with self.assertRaises(ValueError):
            LoggingHook()

    def test_use_alternate_logging_input(self):
        """Construct prehook_msg and posthook_msg such that they provide a tuple of arguments
        rather than an already-formatted string."""

        def prehook_msg(event_name, args, kwargs):
            return ("prehook: event=%s", event_name)

        def posthook_msg(event_name, result):
            return ("posthook: event=%s", event_name)

        hook = LoggingHook(prehook_msg=prehook_msg, posthook_msg=posthook_msg)

        @self.auditor.audit("test.foo", hooks=[hook])
        def foo():
            pass

        with self.auditor.start_auditing():
            foo()

        output = self.logging_output.getvalue().rstrip().split("\n")
        self.assertEqual(output[0], "(DEBUG) prehook: event=test.foo")
        self.assertEqual(output[1], "(DEBUG) posthook: event=test.foo")
