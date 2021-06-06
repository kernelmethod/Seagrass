import cProfile as prof
import logging
import pstats
import typing as t
from io import StringIO


class ProfilerHook:

    profiler: prof.Profile
    restrictions: t.Tuple[t.Any, ...]

    # Set a high prehook_priority and posthook_priority to ensure
    # that the profiler only gets called directly before and after
    # the event.
    prehook_priority: int = 10
    posthook_priority: int = 10

    def __init__(self, restrictions: t.Optional[t.Tuple[t.Any, ...]] = None):
        restrictions = tuple() if restrictions is None else restrictions
        self.restrictions = restrictions
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

    def log_results(self, logger: logging.Logger):
        """Log the results captured by ProfilerHook."""
        # Dump results to an in-memory stream
        output = StringIO()
        stats = self.get_stats(stream=output)
        stats.print_stats(*self.restrictions)

        # Now take results from the in-memory stream and log them using the provided logger.
        logger.info("Results from %s:", self.__class__.__name__)
        logger.info("")
        output.seek(0)
        for line in output.readlines():
            logger.info("    " + line.rstrip())
