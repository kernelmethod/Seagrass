# Testing utilities and base classes for testing Seagrass

import logging
import unittest
from io import StringIO
from seagrass import Auditor


class SeagrassTestCaseBase(unittest.TestCase):
    def setUp(self):
        # Set up an auditor with a basic logging configuration
        self.logging_output = StringIO()
        fh = logging.StreamHandler(self.logging_output)
        fh.setLevel(logging.DEBUG)

        formatter = logging.Formatter("(%(levelname)s) %(message)s")
        fh.setFormatter(formatter)

        self.logger = logging.getLogger("test.seagrass")
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(fh)

        # Create a new auditor instance with the logger we just
        # set up
        self.auditor = Auditor(logger=self.logger)


class HookTestCaseBase(SeagrassTestCaseBase):
    """A base testing class for auditor hooks."""

    def setUp(self):
        super().setUp()

        if hasattr(self, "hook_gen"):
            self.hook = self.hook_gen()
        elif hasattr(self, "hook_class"):
            self.hook = self.hook_class()
        else:
            self.fail(
                "Either 'hook_gen' or 'hook_class' must be defined for children of BaseHookTestCase"
            )
