import logging
import typing as t
from collections import Counter
from seagrass.base import ProtoHook, LoggableHook


class CounterHook(ProtoHook, LoggableHook):

    event_counter: t.Counter[str]

    def __init__(self):
        self.event_counter = Counter()

    def prehook(
        self, event_name: str, args: t.Tuple[t.Any, ...], kwargs: t.Dict[str, t.Any]
    ) -> None:
        self.event_counter[event_name] += 1

    def reset(self):
        self.event_counter.clear()

    def log_results(self, logger: logging.Logger):
        logger.info("Calls to events recorded by %s:", self.__class__.__name__)
        for (event, count) in self.event_counter.items():
            logger.info("    %s: %d", event, count)
