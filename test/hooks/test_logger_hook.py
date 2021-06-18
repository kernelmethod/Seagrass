# Tests for the LoggerHook auditing hook.

import logging
import unittest
from functools import reduce
from operator import add, mul
from seagrass.hooks import LoggingHook
from test.utils import HookTestCaseMixin


class LoggingHookTestCase(HookTestCaseMixin, unittest.TestCase):
    def setUp(self):
        super(HookTestCaseMixin, self).setUp()

        self.hook_pre = LoggingHook(
            prehook_msg=lambda e, args, kwargs: f"hook_pre: {e}, {args=}, {kwargs=}",
        )
        self.hook_both = LoggingHook(
            prehook_msg=lambda e, args, kwargs: f"hook_both: {e}, {args=}, {kwargs=}",
            posthook_msg=lambda e, result: f"hook_both: {e}, {result=}",
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
        self.assertEqual(output[0], f"(DEBUG) hook_pre: {event}, {args=}, kwargs={{}}")
        self.assertEqual(output[1], f"(INFO) hook_both: {event}, {args=}, kwargs={{}}")
        self.assertEqual(output[2], f"(INFO) hook_both: {event}, result={24}")
        self.assertEqual(
            output[3], f"(DEBUG) hook_pre: {event}, {args=}, kwargs={kwargs_add}"
        )
        self.assertEqual(
            output[4], f"(INFO) hook_both: {event}, {args=}, kwargs={kwargs_add}"
        )
        self.assertEqual(output[5], f"(INFO) hook_both: {event}, result={10}")
