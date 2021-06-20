# Tests for ProfilerHook

import time
import unittest
from test.utils import HookTestCaseMixin, req_python_version
from seagrass.base import LogResultsHook, ResettableHook, CleanupHook
from seagrass.hooks import ProfilerHook


class ProfilerHookTestCase(HookTestCaseMixin, unittest.TestCase):

    check_interfaces = (LogResultsHook, ResettableHook, CleanupHook)

    @staticmethod
    def hook_gen():
        return ProfilerHook(sort_keys="cumtime", restrictions=0.1)

    # Test only works for Python >= 3.9 due to the use of StatsProfile
    @req_python_version(min=(3, 9))
    def test_hook_function(self):
        # Note: could just as easily use auditor.audit("test.sleep", time.sleep, ...)
        # here but the name of time.sleep is slightly mangled in the resulting
        # StatsProfile that we generate, which complicates testing.
        @self.auditor.audit("test.sleep", hooks=[self.hook])
        def ausleep(*args):
            time.sleep(*args)

        self.assertEqual(self.hook.get_stats(), None)

        with self.auditor.start_auditing():
            for _ in range(10):
                ausleep(0.001)

        # Get profiler information for ausleep
        stats_profile = self.hook.get_stats().get_stats_profile()
        ausleep_profile = stats_profile.func_profiles["ausleep"]
        self.assertEqual(ausleep_profile.ncalls, "10")

        # Profiler information should be reset after hook.reset() is called
        self.hook.reset()
        self.assertEqual(self.hook.get_stats(), None)

        with self.auditor.start_auditing():
            ausleep(0.01)

        stats_profile = self.hook.get_stats().get_stats_profile()
        ausleep_profile = stats_profile.func_profiles["ausleep"]
        self.assertEqual(ausleep_profile.ncalls, "1")
        self.assertAlmostEqual(ausleep_profile.cumtime, 0.01, delta=0.005)

    # Test only works for Python >= 3.9 due to the use of StatsProfile
    @req_python_version(min=(3, 9))
    def test_hook_nested_functions(self):
        # Ensure that the profiler collects information about nested events
        @self.auditor.audit("test.foo", hooks=[self.hook])
        def foo(*args):
            time.sleep(*args)

        @self.auditor.audit("test.bar", hooks=[self.hook])
        def bar(*args):
            foo(0)
            foo(*args)

        @self.auditor.audit("test.baz", hooks=[self.hook])
        def baz(*args):
            bar(0)
            bar(*args)

        with self.auditor.start_auditing():
            baz(0.05)

        stats_profile = self.hook.get_stats().get_stats_profile()
        foo_profile = stats_profile.func_profiles["foo"]
        bar_profile = stats_profile.func_profiles["bar"]
        baz_profile = stats_profile.func_profiles["baz"]

        self.assertTrue(foo_profile.cumtime >= 0.05)
        self.assertTrue(bar_profile.cumtime >= 0.05)
        self.assertTrue(baz_profile.cumtime >= 0.05)

        self.assertEqual(foo_profile.ncalls, "4")
        self.assertEqual(bar_profile.ncalls, "2")
        self.assertEqual(baz_profile.ncalls, "1")
