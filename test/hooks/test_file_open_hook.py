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
            with self.auditor.audit():
                result = say_hello(f.name, "Alice")

            self.assertEqual(result, "Hello, Alice!\n")
            self.assertEqual(self.hook.file_open_counter[f"{f.name} (mode='w')"], 1)
            self.assertEqual(self.hook.file_open_counter[f"{f.name} (mode='r')"], 1)

            # Check the logging output
            self.auditor.log_results()
            self.logging_output.seek(0)
            lines = [line.rstrip() for line in self.logging_output.readlines()]
            self.assertEqual(len(lines), 3)
            self.assertEqual(lines[1], f"(INFO)     {f.name} (mode='w'): 1")
            self.assertEqual(lines[2], f"(INFO)     {f.name} (mode='r'): 1")


if __name__ == "__main__":
    unittest.main()
