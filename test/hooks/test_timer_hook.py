# Tests for the TimerHook auditing hook

import json
import time
import unittest
from test.utils import HookTestCaseMixin
from seagrass.base import LogResultsHook, ResettableHook
from seagrass.hooks import TimerHook


class TimerHookTestCase(HookTestCaseMixin, unittest.TestCase):

    hook_gen = TimerHook
    check_interfaces = (LogResultsHook, ResettableHook)

    def test_hook_function(self):
        ausleep = self.auditor.audit("test.time.sleep", time.sleep, hooks=[self.hook])

        ausleep(0.01)
        with self.auditor.start_auditing():
            ausleep(0.01)
        ausleep(0.01)

        recorded_time = self.hook.event_times["test.time.sleep"]
        self.assertAlmostEqual(recorded_time, 0.01, delta=0.005)

        # Check logging output
        self.auditor.log_results()
        self.logging_output.seek(0)
        output = [line.rstrip() for line in self.logging_output.readlines()]
        output = [json.loads(line) for line in output]

        self.assertTrue(all(o.get("level") == "INFO" for o in output))
        self.assertEqual(len(output), 1)
        self.assertEqual(output[0]["message"], "TimerHook results")
        self.assertEqual(output[0]["seagrass"]["hook"], "TimerHook")
        self.assertEqual(output[0]["seagrass"]["hook_ctx"]["event"], "test.time.sleep")
        self.assertEqual(output[0]["seagrass"]["hook_ctx"]["time"], recorded_time)


if __name__ == "__main__":
    unittest.main()
