import cProfile as prof
import pstats
import typing as t
from seagrass.hooks import ProtoHook


class ProfilerHook(ProtoHook):

    profiler: prof.Profile

    # Set a high prehook_priority and posthook_priority to ensure
    # that the profiler only gets called directly before and after
    # the event.
    prehook_priority: int = 10
    posthook_priority: int = 10

    def __init__(self):
        self.reset()

    def prehook(
        self, event_name: str, args: t.Tuple[t.Any, ...], kwargs: t.Dict[str, t.Any]
    ) -> None:
        # Start profiling
        self.profiler.enable()

    def posthook(self, event_name: str, result: t.Any, context: None):
        # Stop profiling
        self.profiler.disable()

    def get_stats(self, **kwargs) -> pstats.Stats:
        """Return the profiling statistics as a pstats.Stats class."""
        return pstats.Stats(self.profiler, **kwargs)

    def reset(self) -> None:
        """Reset the internal profiler."""
        self.profiler = prof.Profile()
