# Tests for Auditor creation and basic functionality

import logging
import unittest
from io import StringIO
from seagrass import Auditor


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

    def test_define_two_events_with_the_same_name(self):
        # If we try to create two auditing events with the same name, we should
        # get an error.
        auditor = Auditor()

        @auditor.decorate("test.foo")
        def foo_1():
            return

        with self.assertRaises(ValueError):

            @auditor.decorate("test.foo")
            def foo_2():
                return


if __name__ == "__main__":
    unittest.main()
