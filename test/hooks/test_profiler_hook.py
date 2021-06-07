# Tests for ProfilerHook

from seagrass import Auditor
from seagrass.hooks import ProfilerHook
import time
import unittest


class ProfilerHookTestCase(unittest.TestCase):
    def test_hook_function(self):
        # Test only works for Python >= 3.9 due to the use of StatsProfile
        try:
            from pstats import StatsProfile  # noqa: F401
        except ImportError:
            self.skipTest("Test disabled for Python < 3.9")

        auditor = Auditor()
        hook = ProfilerHook()

        # Note: could just as easily use auditor.wrap(time.sleep, ...) here
        # but the name of time.sleep is slightly mangled in the resulting
        # StatsProfile that we generate, which complicates testing.
        @auditor.decorate("test.sleep", hooks=[hook])
        def ausleep(*args):
            time.sleep(*args)

        with auditor.audit():
            for _ in range(10):
                ausleep(0.001)

        # Get profiler information for ausleep
        stats_profile = hook.get_stats().get_stats_profile()
        ausleep_profile = stats_profile.func_profiles["ausleep"]
        self.assertEqual(ausleep_profile.ncalls, "10")

        # Profiler information should be reset after hook.reset() is called
        hook.reset()
        with self.assertRaises(Exception):
            hook.get_stats()

        with auditor.audit():
            ausleep(0.01)

        stats_profile = hook.get_stats().get_stats_profile()
        ausleep_profile = stats_profile.func_profiles["ausleep"]
        self.assertEqual(ausleep_profile.ncalls, "1")
        self.assertAlmostEqual(ausleep_profile.cumtime, 0.01, delta=0.005)
