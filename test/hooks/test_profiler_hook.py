# Tests for ProfilerHook

import time
import unittest
from test.base import HookTestCaseMixin
from seagrass.hooks import ProfilerHook


class ProfilerHookTestCase(HookTestCaseMixin, unittest.TestCase):

    check_is_log_results_hook = True

    @staticmethod
    def hook_gen():
        return ProfilerHook(sort_keys="cumtime", restrictions=0.1)

    def test_hook_function(self):
        # Test only works for Python >= 3.9 due to the use of StatsProfile
        try:
            from pstats import StatsProfile  # noqa: F401
        except ImportError:
            self.skipTest("Test disabled for Python < 3.9")

        # Note: could just as easily use auditor.wrap(time.sleep, ...) here
        # but the name of time.sleep is slightly mangled in the resulting
        # StatsProfile that we generate, which complicates testing.
        @self.auditor.decorate("test.sleep", hooks=[self.hook])
        def ausleep(*args):
            time.sleep(*args)

        self.assertEqual(self.hook.get_stats(), None)

        with self.auditor.audit():
            for _ in range(10):
                ausleep(0.001)

        # Get profiler information for ausleep
        stats_profile = self.hook.get_stats().get_stats_profile()
        ausleep_profile = stats_profile.func_profiles["ausleep"]
        self.assertEqual(ausleep_profile.ncalls, "10")

        # Profiler information should be reset after hook.reset() is called
        self.hook.reset()
        self.assertEqual(self.hook.get_stats(), None)

        with self.auditor.audit():
            ausleep(0.01)

        stats_profile = self.hook.get_stats().get_stats_profile()
        ausleep_profile = stats_profile.func_profiles["ausleep"]
        self.assertEqual(ausleep_profile.ncalls, "1")
        self.assertAlmostEqual(ausleep_profile.cumtime, 0.01, delta=0.005)
