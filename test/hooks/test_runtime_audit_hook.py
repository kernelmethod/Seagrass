# Tests for the RuntimeAuditHook abstract base class.

import tempfile
import unittest
from seagrass.base import CleanupHook
from seagrass.hooks import RuntimeAuditHook
from test.utils import HookTestCaseMixin


class RuntimeHookTestCaseMixin(HookTestCaseMixin):
    check_interfaces = (CleanupHook,)


class FileOpenRuntimeAuditTestCase(HookTestCaseMixin, unittest.TestCase):
    """Build an auditing hook for tracking file opens out of RuntimeAuditHook, similar to
    FileOpenHook."""

    class _Hook(RuntimeAuditHook):
        def __init__(self):
            super().__init__()
            self.total_file_opens = 0

        def sys_hook(self, event_name, args):
            if event_name == "open":
                self.total_file_opens += 1
                self.opened_filename = args[0]
                self.opened_mode = args[1]

    hook_gen = _Hook

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


if __name__ == "__main__":
    unittest.main()
