# Testing utilities and base classes for testing Seagrass

import logging
import typing as t
from io import StringIO
from seagrass import Auditor
from seagrass.base import ProtoHook, LogResultsHook, ResettableHook


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
    hook_gen: t.Optional[t.Callable[[], ProtoHook]] = None

    check_is_log_results_hook: bool = False
    check_is_resettable_hook: bool = False

    @property
    def hook_name(self) -> str:
        return self.hook.__class__.__name__

    def setUp(self):
        super().setUp()

        if self.hook_gen is not None:
            self.hook = self.hook_gen()

    def test_hook_satisfies_interfaces(self):
        CheckableProtoHook = t.runtime_checkable(ProtoHook)
        self.assertIsInstance(
            self.hook,
            CheckableProtoHook,
            f"{self.hook_name} does not satisfy the ProtoHook interface",
        )

        if self.check_is_log_results_hook:
            self.assertIsInstance(
                self.hook,
                LogResultsHook,
                f"{self.hook_name} does not satisfy the LogResultsHook interface",
            )

        if self.check_is_resettable_hook:
            self.assertIsInstance(
                self.hook,
                ResettableHook,
                f"{self.hook_name} does not satisfy the ResettableHook interface",
            )
