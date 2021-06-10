# Tests for protocols and functions defined in seagrass.base

import seagrass.base as base
import typing as t
import unittest


class CustomHookImplementationTestCase(unittest.TestCase):
    def setUp(self):
        # Create a version of the ProtoHook protocol that we can check at runtime.
        self.CheckableProtoHook = t.runtime_checkable(base.ProtoHook)

    def test_get_prehook_and_posthook_priority(self):
        class MyHook:
            prehook_priority: int = 7

            def prehook(self, *args):
                ...

            def posthook(self, *args):
                ...

        hook = MyHook()
        self.assertIsInstance(
            hook,
            self.CheckableProtoHook,
            f"{hook.__class__.__name__} does not satisfy the hooking protocol",
        )
        self.assertEqual(base.prehook_priority(hook), 7)
        self.assertEqual(base.posthook_priority(hook), base.DEFAULT_POSTHOOK_PRIORITY)

        # The prehook_priority and posthook_priority are both required to be integers
        hook.prehook_priority = "Alice"
        with self.assertRaises(TypeError):
            base.prehook_priority(hook)

        hook.posthook_priority = None
        with self.assertRaises(TypeError):
            base.posthook_priority(hook)


if __name__ == "__main__":
    unittest.main()
