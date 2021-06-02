# Tests for the LoggerHook auditing hook.

import logging
import unittest
from functools import reduce
from io import StringIO
from seagrass import Auditor
from seagrass.hooks import LoggingHook
from operator import add, mul


class LoggingHookTestCase(unittest.TestCase):
    def setUp(self):
        self.logging_output = StringIO()
        self.logger = logging.getLogger("logging_test_case")
        self.logger.setLevel(logging.DEBUG)

        fh = logging.StreamHandler(self.logging_output)
        fh.setLevel(logging.DEBUG)

        formatter = logging.Formatter("%(message)s")
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)

    def test_hook_function(self):
        auditor = Auditor(logger=self.logger)
        hook_pre = LoggingHook(
            prehook_msg=lambda e, args, kwargs: f"(prehook) hook_pre: {e}, {args=}, {kwargs=}"
        )
        hook_both = LoggingHook(
            prehook_msg=lambda e, args, kwargs: f"(prehook) hook_both: {e}, {args=}, {kwargs=}",
            posthook_msg=lambda e, result: f"(posthook) hook_both: {e}, {result=}",
        )

        event = "test.multiply_or_add"

        @auditor.decorate(event, hooks=[hook_pre, hook_both])
        def multiply_or_add(*args, op="*"):
            if op == "*":
                return reduce(mul, args, 1)
            elif op == "+":
                return reduce(add, args, 0)
            else:
                raise ValueError(f"Unknown operation '{op}'")

        args = (1, 2, 3, 4)
        kwargs_add = {"op": "+"}
        with auditor.audit():
            multiply_or_add(*args)
            multiply_or_add(*args, **kwargs_add)

        self.logging_output.seek(0)
        output = self.logging_output.read().rstrip().split("\n")
        self.assertEqual(
            output[0], f"(prehook) hook_pre: {event}, {args=}, kwargs={{}}"
        )
        self.assertEqual(
            output[1], f"(prehook) hook_both: {event}, {args=}, kwargs={{}}"
        )
        self.assertEqual(output[2], f"(posthook) hook_both: {event}, result={24}")
        self.assertEqual(
            output[3], f"(prehook) hook_pre: {event}, {args=}, kwargs={kwargs_add}"
        )
        self.assertEqual(
            output[4], f"(prehook) hook_both: {event}, {args=}, kwargs={kwargs_add}"
        )
        self.assertEqual(output[5], f"(posthook) hook_both: {event}, result={10}")
