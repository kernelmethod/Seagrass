# Testing utilities and base classes for testing Seagrass

import logging
import typing as t
from io import StringIO
from seagrass import Auditor
from seagrass.base import ProtoHook, LogResultsHook


class SeagrassTestCaseMixin:

    logging_output: StringIO
    logger: logging.Logger
    auditor: Auditor

    def setUp(self) -> None:
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


class HookTestCaseMixin(SeagrassTestCaseMixin):
    """A base testing class for auditor hooks."""

    hook: ProtoHook
    hook_gen: t.Callable[[], ProtoHook]
    check_is_log_results_hook: bool = False

    def setUp(self):
        super().setUp()
        self.hook = self.hook_gen()

    def test_hook_satisfies_interfaces(self):
        CheckableProtoHook = t.runtime_checkable(ProtoHook)
        self.assertTrue(isinstance(self.hook, CheckableProtoHook))

        if self.check_is_log_results_hook:
            self.assertTrue(isinstance(self.hook, LogResultsHook))
