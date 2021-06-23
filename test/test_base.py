# Tests for protocols and functions defined in seagrass.base

import seagrass.base as base
import typing as t
import unittest


class CustomHookImplementationTestCase(unittest.TestCase):
    def setUp(self):
        # Create a version of the ProtoHook protocol that we can check at runtime.
        self.CheckableProtoHook = t.runtime_checkable(base.ProtoHook)

    def test_get_prehook_and_posthook_priority(self):
        class MyHook(base.ProtoHook[None]):
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
        self.assertEqual(hook.prehook_priority, 7)
        self.assertEqual(hook.posthook_priority, base.DEFAULT_POSTHOOK_PRIORITY)


if __name__ == "__main__":
    unittest.main()
