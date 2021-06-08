# Tests for protocols and functions defined in seagrass.base

import seagrass.base as base
import unittest


class CustomHookImplementationTestCase(unittest.TestCase):
    def test_get_prehook_and_posthook_priority(self):
        class MyHook:
            prehook_priority: int = 7

            def prehook(self, *args):
                ...

            def posthook(self, *args):
                ...

            def reset(self):
                ...

        hook = MyHook()
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
