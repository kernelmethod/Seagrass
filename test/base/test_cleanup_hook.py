# Tests for hook satisfying the CleanupHook interface.

import unittest
from seagrass.base import ProtoHook, CleanupHook, ResettableHook
from seagrass.errors import PosthookError
from test.utils import SeagrassTestCaseMixin


class CleanupHookTestCase(SeagrassTestCaseMixin, unittest.TestCase):
    """Tests to check that the cleanup stage of hooks that satisfy the CleanupHook interface
    is unconditionally executed."""

    class _BaseTestHook(ProtoHook[None]):
        def __init__(self):
            self.reset()

        def prehook(self, *args):
            pass

        def reset(self):
            self.counter = 0

    class _HookA(_BaseTestHook):
        # Regular hook with no cleanup stage
        def posthook(self, *args):
            self.counter += 1

    class _HookB(_BaseTestHook):
        # A hook that satisfies the CleanupHook interface
        def posthook(self, *args):
            pass

        def cleanup(self, *args):
            self.counter += 1

    class _HookC(_BaseTestHook):
        # A hook that satisfies the CleanupHook interface, but which also raises an
        # exception in its posthook.
        def posthook(self, *args):
            assert False

        def cleanup(self, *args):
            self.counter += 1

    class _HookD(_BaseTestHook):
        # A hook that satisfies the CleanupHook interface, but which also raises an
        # exception in its prehook.
        def prehook(self, *args):
            assert False

        def posthook(self, *args):
            pass

        def cleanup(self, *args):
            self.counter += 1

    def setUp(self):
        super().setUp()
        self.hook_a = self._HookA()
        self.hook_b = self._HookB()
        self.hook_c = self._HookC()
        self.hook_d = self._HookD()
        self.hooks = (self.hook_a, self.hook_b, self.hook_c, self.hook_d)

    def test_hooks_satisfy_interfaces(self):
        # All of the hooks, except for _HookA, should satisfy the CleanupHook interface.
        self.assertNotIsInstance(self.hooks[0], CleanupHook)
        for hook in self.hooks[1:]:
            self.assertIsInstance(hook, CleanupHook)

        # All of the hook should satisfy the ResettableHook interface
        for hook in self.hooks:
            self.assertIsInstance(hook, ResettableHook)

    def _create_test_functions(self, event_name_prefix, *hooks):
        """Hook two test functions: one that does nothing, and other that raises a RuntimeError."""

        @self.auditor.audit(f"{event_name_prefix}.no_error", hooks=hooks)
        def no_error():
            return

        @self.auditor.audit(f"{event_name_prefix}.error", hooks=hooks)
        def error():
            raise RuntimeError()

        return no_error, error

    def test_hooks_a_and_b(self):
        # Tests for _HookA + _HookB
        nerr, err = self._create_test_functions("hook_ab", self.hook_a, self.hook_b)
        with self.auditor.start_auditing(reset_hooks=True):
            nerr()
            self.assertEqual(self.hook_a.counter, 1)
            self.assertEqual(self.hook_b.counter, 1)

            with self.assertRaises(RuntimeError):
                err()
            self.assertEqual(self.hook_a.counter, 1)
            self.assertEqual(self.hook_b.counter, 2)

    def test_hooks_b_and_c(self):
        # Tests for _HookC + _HookB
        nerr, err = self._create_test_functions("hook_cb", self.hook_c, self.hook_b)
        with self.auditor.start_auditing(reset_hooks=True):
            with self.assertRaises(PosthookError):
                nerr()
            self.assertEqual(self.hook_b.counter, 1)
            self.assertEqual(self.hook_c.counter, 1)

            # Despite the fact that an error is raised in the posthook, we should prioritize
            # the error that was raised by the wrapped function.
            with self.assertRaises(RuntimeError):
                err()
            self.assertEqual(self.hook_b.counter, 2)
            self.assertEqual(self.hook_c.counter, 2)

    def test_hooks_b_and_d(self):
        # Tests for _HookD + _HookB, and _HookB + _HookD
        #
        # For these test cases, we have to consider the fact that cleanup is only called on
        # the hooks whose prehooks were executed. As a result:
        # - When we call _HookD before _HookB, we error out *before* reaching _HookB's prehook, so
        #   we never call cleanup on _HookB.
        # - When we call _HookD after _HookB, we error out *after* reaching _HookB's prehook, so
        #   cleanup *should* be called on _HookB.

        nerr, err = self._create_test_functions("hook_db", self.hook_d, self.hook_b)
        with self.auditor.start_auditing(reset_hooks=True):
            with self.assertRaises(AssertionError):
                nerr()
            self.assertEqual(self.hook_b.counter, 0)
            self.assertEqual(self.hook_d.counter, 0)

            with self.assertRaises(AssertionError):
                err()
            self.assertEqual(self.hook_b.counter, 0)
            self.assertEqual(self.hook_d.counter, 0)

        nerr, err = self._create_test_functions("hook_bd", self.hook_b, self.hook_d)
        with self.auditor.start_auditing(reset_hooks=True):
            with self.assertRaises(AssertionError):
                nerr()
            self.assertEqual(self.hook_b.counter, 1)
            self.assertEqual(self.hook_d.counter, 0)

            with self.assertRaises(AssertionError):
                err()
            self.assertEqual(self.hook_b.counter, 2)
            self.assertEqual(self.hook_d.counter, 0)
