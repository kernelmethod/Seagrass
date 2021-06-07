# Tests for the FileOpenHook auditing hook.

import tempfile
import unittest
from test.base import HookTestCaseBase
from seagrass.hooks import FileOpenHook


class FileOpenHookTestCase(HookTestCaseBase):

    hook_class = FileOpenHook

    def test_hook_function(self):
        @self.auditor.decorate("test.say_hello", hooks=[self.hook])
        def say_hello(filename, name) -> str:
            with open(filename, "w") as f:
                f.write(f"Hello, {name}!\n")

            with open(filename, "r") as f:
                return f.read()

        with tempfile.NamedTemporaryFile() as f:
            # Even though we're using sys.audit hooks, calls to say_hello should not
            # trigger the audit hook unless we're in an auditing context.
            say_hello(f.name, "Alice")
            with self.auditor.audit():
                result = say_hello(f.name, "Alice")
            say_hello(f.name, "Alice")

            self.assertEqual(result, "Hello, Alice!\n")

            keys = list(self.hook.file_open_counter["test.say_hello"].keys())
            keys.sort(key=lambda info: info.mode)
            self.assertEqual(keys[0].filename, f.name)
            self.assertEqual(keys[0].mode, "r")
            self.assertEqual(keys[1].filename, f.name)
            self.assertEqual(keys[1].mode, "w")

            # Check the logging output
            self.auditor.log_results()
            self.logging_output.seek(0)
            lines = [line.rstrip() for line in self.logging_output.readlines()]

            # Header line + one line for one event + two lines for one read of the temporary
            # file, one write to it
            self.assertEqual(len(lines), 4)


if __name__ == "__main__":
    unittest.main()
