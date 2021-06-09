# Tests for the TimerHook auditing hook

import time
import unittest
from test.base import HookTestCaseMixin
from seagrass.hooks import TimerHook


class TimerHookTestCase(HookTestCaseMixin, unittest.TestCase):

    hook_gen = TimerHook
    check_is_log_results_hook = True

    def test_hook_function(self):
        ausleep = self.auditor.wrap(time.sleep, "test.time.sleep", hooks=[self.hook])

        ausleep(0.01)
        with self.auditor.audit():
            ausleep(0.01)
        ausleep(0.01)

        recorded_time = self.hook.event_times["test.time.sleep"]
        self.assertAlmostEqual(recorded_time, 0.01, delta=0.005)

        # Check logging output
        self.auditor.log_results()
        self.logging_output.seek(0)
        output = [line.rstrip() for line in self.logging_output.readlines()]
        self.assertEqual(output[0], "(INFO) TimerHook results:")
        self.assertEqual(
            output[1], "(INFO)     Time spent in test.time.sleep: %f" % recorded_time
        )


if __name__ == "__main__":
    unittest.main()
