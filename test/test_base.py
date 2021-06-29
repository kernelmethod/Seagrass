# Tests for protocols and functions defined in seagrass.base

import seagrass.base as base
import seagrass._typing as t
import unittest


class CustomHookImplementationTestCase(unittest.TestCase):
    def setUp(self):
        # Create a version of the ProtoHook protocol that we can check at runtime.
        self.CheckableProtoHook = t.runtime_checkable(base.ProtoHook)

    def test_get_hook_priority(self):
        class MyHook(base.ProtoHook[None]):
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
        self.assertEqual(hook.priority, base.DEFAULT_PRIORITY)


if __name__ == "__main__":
    unittest.main()
