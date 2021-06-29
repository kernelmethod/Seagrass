# Testing utilities and base classes for testing Seagrass

import asyncio
import logging
import logging.config
import sys
import seagrass._typing as t
from functools import wraps
from io import StringIO
from seagrass import Auditor
from seagrass.base import ProtoHook


def async_test(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(func(*args, **kwargs))

    return wrapper


class SeagrassTestCaseMixin:

    logging_output: StringIO
    logger: logging.Logger
    auditor: Auditor

    # Whether to emit logs that are >= WARNING to stdout
    log_warnings_to_stdout: bool = True

    def setUp(self) -> None:
        # Set up logging configuration
        self.logging_output = StringIO()

        handlers = ["default"]
        if self.log_warnings_to_stdout:
            handlers.append("warnings")

        config = {
            "version": 1,
            "disable_existing_loggers": True,
            "formatters": {
                "standard": {
                    "format": "(%(levelname)s) %(message)s",
                },
            },
            "handlers": {
                "default": {
                    "level": "DEBUG",
                    "formatter": "standard",
                    "class": "logging.StreamHandler",
                    "stream": self.logging_output,
                },
                # Add an additional handler for warnings that goes out to stdout. This way, if
                # any warnings/errors show up during tests, we can view them in the test output.
                "warnings": {
                    "level": "WARNING",
                    "formatter": "standard",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
            },
            "loggers": {
                "test.seagrass": {
                    "handlers": handlers,
                    "level": "DEBUG",
                    "propagate": False,
                },
            },
        }

        logging.config.dictConfig(config)
        self.logger = logging.getLogger("test.seagrass")

        # Create a new auditor instance with the logger we just
        # set up
        self.auditor = Auditor(logger=self.logger)


class HookTestCaseMixin(SeagrassTestCaseMixin):
    """A base testing class for auditor hooks."""

    hook: ProtoHook
    hook_gen: t.Optional[t.Callable[[], ProtoHook]] = None

    # A list of all of the interfaces that the hook is expected
    # to satisfy.
    check_interfaces: t.Optional[t.Tuple[t.Type, ...]] = None

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

        interfaces = [] if self.check_interfaces is None else self.check_interfaces

        for interface in interfaces:
            self.assertIsInstance(
                self.hook,
                interface,
                f"{self.hook_name} does not satisfy the {interface.__name__} interface",
            )


F = t.Callable[..., None]


def req_python_version(
    min: t.Optional[t.Tuple[int, int]] = None, max: t.Optional[t.Tuple[int, int]] = None
) -> t.Callable[[F], F]:
    """Create a wrapper around a unit test to enforce a minimum
    or maximum Python version."""

    assert min is not None or max is not None
    version = sys.version_info

    err_msg = f"Test skipped: disabled for Python version = {version.major}.{version.minor}.{version.micro}, required"
    bad_version = False
    if (min is not None and max is not None) and (version < min or max < version):
        err_msg = f"{err_msg} {min[0]}.{min[1]} <= version <= {max[0]}.{max[1]}"
        bad_version = True
    elif (min is not None and max is None) and (version < min):
        err_msg = f"{err_msg} version >= {min[0]}.{min[1]}"
        bad_version = True
    elif (min is None and max is not None) and (version >= max):
        err_msg = f"{err_msg} version < {max[0]}.{max[1]}"
        bad_version = True

    if not bad_version:

        def decorator(test_func: F) -> F:
            return test_func

        return decorator
    else:

        def decorator(test_func: F) -> F:
            @wraps(test_func)
            def wrapper(self, *args, **kwargs):
                self.skipTest(err_msg)

            return wrapper

        return decorator
