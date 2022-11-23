# Additional tests for Sseagrass logging functionality

import json
import unittest
from seagrass import get_audit_logger
from test.utils import SeagrassTestCaseMixin


class AuditorLoggingTestCase(SeagrassTestCaseMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()

    def test_log_events(self):
        @self.auditor.audit("myevent.foo")
        def foo():
            logger = get_audit_logger()
            if logger is not None:
                logger.info("hello, world!")

        @self.auditor.audit("myevent.bar")
        def bar():
            foo()
            logger = get_audit_logger()
            if logger is not None:
                logger.info("calling event bar")

        with self.auditor.start_auditing():
            bar()

        # Check that the event was written to the log
        output = self.logging_output.getvalue()[:-1].split("\n")
        output = [json.loads(o) for o in output]
        self.assertEqual(len(output), 2)
        self.assertTrue(all(o["level"] == "INFO" for o in output))

        self.assertEqual(output[0]["message"], "hello, world!")
        self.assertEqual(output[1]["message"], "calling event bar")

        self.assertEqual(output[0]["seagrass"]["event"], "myevent.foo")
        self.assertEqual(output[1]["seagrass"]["event"], "myevent.bar")

    def test_log_outside_of_event(self):
        self.auditor.logger.debug("log outside event")
        output = self.logging_output.getvalue()[:-1]
        output = json.loads(output)
        self.assertEqual(output["level"], "DEBUG")
        self.assertEqual(output["seagrass"]["event"], None)
        self.assertEqual(output["message"], "log outside event")


if __name__ == "__main__":
    unittest.main()
