# Tests for the RuntimeAuditHook abstract base class.

import sys
import tempfile
import unittest
from seagrass.base import CleanupHook
from seagrass.hooks import RuntimeAuditHook
from test.utils import HookTestCaseMixin, req_python_version


class RuntimeHookTestCaseMixin(HookTestCaseMixin):
    check_interfaces = (CleanupHook,)


# Example hooks that subclass RuntimeAuditHook


class FileOpenTestHook(RuntimeAuditHook):
    """A simple RuntimeAuditHook that tracks file opens. This is a simplified version of
    FileOpenHook."""

    def __init__(self):
        super().__init__(self.sys_hook, traceable=True)
        self.total_file_opens = 0

    def sys_hook(self, event_name, args):
        if event_name == "open":
            self.total_file_opens += 1
            self.opened_filename = args[0]
            self.opened_mode = args[1]


class ErroneousHook(RuntimeAuditHook):
    """A runtime audit hook that raises an error whenever sys_hook gets called."""

    def __init__(self):
        super().__init__(self.sys_hook, propagate_errors=False, traceable=True)

    def sys_hook(self, event, args):
        raise ValueError("my_test_message")


# Test cases


class FileOpenRuntimeHookTestCase(RuntimeHookTestCaseMixin, unittest.TestCase):
    """Build an auditing hook for tracking file opens out of RuntimeAuditHook, similar to
    FileOpenHook."""

    hook_gen = FileOpenTestHook

    # These test cases require the use of sys.audit and sys.addaudithook, so they're disabled
    # for Python versions < 3.8
    @req_python_version(min=(3, 8))
    def setUp(self):
        super().setUp()

    def test_hook_function(self):
        @self.auditor.audit("test.say_hello", hooks=[self.hook])
        def say_hello(filename) -> str:
            with open(filename, "w") as f:
                f.write("Hello!\n")

            with open(filename, "r") as f:
                return f.read()

        with tempfile.NamedTemporaryFile() as f:
            # Even though we're using sys.audit hooks, calls to say_hello should not
            # trigger the audit hook unless we're in an auditing context.
            say_hello(f.name)
            with self.auditor.start_auditing():
                say_hello(f.name)
            say_hello(f.name)

            self.assertEqual(self.hook.total_file_opens, 2)
            self.assertEqual(self.hook.opened_filename, f.name)
            self.assertEqual(self.hook.opened_mode, "r")

    def test_default_error_propagation_behavior(self):
        self.assertEqual(
            self.hook.propagate_errors, RuntimeAuditHook.PROPAGATE_ERRORS_DEFAULT
        )

    def test_hook_works_if_an_exception_is_raised(self):
        # In the case where an exception is raised in the body of the function, the hook
        # should still work correctly.
        @self.auditor.audit("test.erroneous_func", hooks=[self.hook])
        def erroneous_func(filename):
            with open(filename, "w") as f:
                f.write("Hello!\n")

            # Artificially raise an error at this point
            assert False

        def try_erroneous_func(filename):
            try:
                return erroneous_func(filename)
            except:
                pass

        with tempfile.NamedTemporaryFile() as f:
            try_erroneous_func(f.name)
            with self.auditor.start_auditing():
                try_erroneous_func(f.name)
            try_erroneous_func(f.name)

            self.assertEqual(self.hook.total_file_opens, 1)


class ErroneousRuntimeHookTestCase(RuntimeHookTestCaseMixin, unittest.TestCase):
    """Tests for hook classes that inherit from RuntimeHook that raise an error in
    their sys_hook function."""

    hook_gen = ErroneousHook

    @req_python_version(min=(3, 8))
    def setUp(self):
        super().setUp()

        @self.auditor.audit("my_event", hooks=[self.hook])
        def my_event():
            sys.audit("sys.my_event")

        self.my_event = my_event

    def test_hook_with_no_propagation(self):
        # When error propagation is disabled, errors should instead be logged
        with self.auditor.start_auditing():
            self.my_event()
        output = self.logging_output.getvalue().rstrip()
        self.assertEqual(
            output,
            "(ERROR) ValueError raised in ErroneousHook.sys_hook: my_test_message",
        )

    def test_hook_with_propagation(self):
        self.hook.propagate_errors = True
        with self.auditor.start_auditing():
            with self.assertRaises(ValueError):
                self.my_event()


class RaiseExceptionForPythonBefore38(unittest.TestCase):
    """RuntimeAuditHook tests that should be run for Python versions before 3.8, when sys.audit
    and sys.addaudithook were added."""

    @req_python_version(max=(3, 8))
    def setUp(self):
        pass

    def test_get_error_when_creating_hook(self):
        with self.assertRaises(NotImplementedError):
            _ = FileOpenTestHook()

        with self.assertRaises(NotImplementedError):
            _ = ErroneousHook()


if __name__ == "__main__":
    unittest.main()
