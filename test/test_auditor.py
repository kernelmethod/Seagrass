# Tests for Auditor creation and basic functionality

import unittest
from seagrass import Auditor


class CreateAuditorTestCase(unittest.TestCase):
    """Tests for creating a new Auditor instance."""

    def test_create_auditor_with_logger(self):
        import logging
        from io import StringIO

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


if __name__ == "__main__":
    unittest.main()
