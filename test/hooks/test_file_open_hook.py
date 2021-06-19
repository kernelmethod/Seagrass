# Tests for the FileOpenHook auditing hook.

import tempfile
import unittest
from test.utils import HookTestCaseMixin
from seagrass.base import LogResultsHook, ResettableHook, CleanupHook
from seagrass.hooks import FileOpenHook


class FileOpenHookTestCase(HookTestCaseMixin, unittest.TestCase):

    check_interfaces = (LogResultsHook, ResettableHook, CleanupHook)

    @staticmethod
    def hook_gen():
        return FileOpenHook()

    def test_hook_function(self):
        @self.auditor.audit("test.say_hello", hooks=[self.hook])
        def say_hello(filename, name) -> str:
            with open(filename, "w") as f:
                f.write(f"Hello, {name}!\n")

            with open(filename, "r") as f:
                return f.read()

        with tempfile.NamedTemporaryFile() as f:
            # Even though we're using sys.audit hooks, calls to say_hello should not
            # trigger the audit hook unless we're in an auditing context.
            say_hello(f.name, "Alice")
            with self.auditor.start_auditing():
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
        # Opens that occur in an event that's nested in another event should only count for
        # the inner event, not the outer one.
        @self.auditor.audit("test.readlines", hooks=[self.hook])
        def readlines(filename):
            with open(filename, "r") as f:
                return f.readlines()

        @self.auditor.audit("test.tabify", hooks=[self.hook])
        def tabify(filename, outfile):
            lines = readlines(filename)
            with open(outfile, "w") as f:
                for line in lines:
                    f.write("\t" + line)

        with tempfile.NamedTemporaryFile() as tf1:
            with tempfile.NamedTemporaryFile() as tf2:
                with self.auditor.start_auditing():
                    with open(tf1.name, "w") as f:
                        f.write("hello\nworld!")
                    tabify(tf1.name, tf2.name)

                self.assertEqual(
                    sorted(self.hook.file_open_counter.keys()),
                    ["test.readlines", "test.tabify"],
                )

                readlines_keys = list(
                    self.hook.file_open_counter["test.readlines"].keys()
                )
                tabify_keys = list(self.hook.file_open_counter["test.tabify"].keys())

                # Opened one file for reading in readlines
                # Opened one file for writing in tabify
                self.assertEqual(len(readlines_keys), 1)
                self.assertEqual(len(tabify_keys), 1)

                # Check statistics about the file that was read
                read_info = readlines_keys[0]
                self.assertEqual(read_info.filename, tf1.name)
                self.assertEqual(read_info.mode, "r")
                self.assertEqual(
                    self.hook.file_open_counter["test.readlines"][read_info], 1
                )
                self.assertEqual(
                    self.hook.file_open_counter["test.tabify"][read_info], 0
                )

                # Check statistics about the file that was written to
                write_info = tabify_keys[0]
                self.assertEqual(write_info.filename, tf2.name)
                self.assertEqual(write_info.mode, "w")
                self.assertEqual(
                    self.hook.file_open_counter["test.readlines"][write_info], 0
                )
                self.assertEqual(
                    self.hook.file_open_counter["test.tabify"][write_info], 1
                )


if __name__ == "__main__":
    unittest.main()
