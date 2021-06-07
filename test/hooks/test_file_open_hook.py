# Tests for the FileOpenHook auditing hook.

import tempfile
import unittest
from test.base import HookTestCaseBase
from seagrass.hooks import FileOpenHook


class FileOpenHookTestCase(HookTestCaseBase):

    # We set track_nested_opens = True so that if we call open() in an event that's
    # nested in another event, we will count the open() for both events.
    @staticmethod
    def hook_gen():
        return FileOpenHook(track_nested_opens=True)

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

    def test_nested_calls_to_hooked_functions(self):
        @self.auditor.decorate("test.readlines", hooks=[self.hook])
        def readlines(filename):
            with open(filename, "r") as f:
                return f.readlines()

        @self.auditor.decorate("test.tabify", hooks=[self.hook])
        def tabify(filename):
            return ["\t" + line for line in readlines(filename)]

        with tempfile.NamedTemporaryFile() as f:
            with self.auditor.audit():
                with open(f.name, "w") as f:
                    f.write("hello\nworld!")
                tabify(f.name)

            self.assertEqual(
                sorted(self.hook.file_open_counter.keys()),
                ["test.readlines", "test.tabify"],
            )

            readlines_keys = list(self.hook.file_open_counter["test.readlines"].keys())
            tabify_keys = list(self.hook.file_open_counter["test.tabify"].keys())

            # Only opened one file in our events, and only for reading
            self.assertEqual(len(readlines_keys), 1)
            self.assertEqual(len(tabify_keys), 1)
            self.assertEqual(readlines_keys[0], tabify_keys[0])

            open_info = readlines_keys[0]
            self.assertEqual(open_info.filename, f.name)
            self.assertEqual(open_info.mode, "r")
            self.assertEqual(
                self.hook.file_open_counter["test.readlines"][open_info], 1
            )
            self.assertEqual(self.hook.file_open_counter["test.tabify"][open_info], 1)


if __name__ == "__main__":
    unittest.main()
