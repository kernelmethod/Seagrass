import logging
import seagrass._typing as t
from collections import Counter
from seagrass.base import ProtoHook
from ._utils import HookContext


class CounterHook(ProtoHook[None]):
    """A Seagrass hook that counts the number of times an event occurs.

    **Examples:**

    .. testsetup:: counterhook-examples

       from seagrass import Auditor
       from seagrass._docs import configure_logging

       configure_logging()
       auditor = Auditor()

    .. doctest:: counterhook-examples

       >>> from seagrass.hooks import CounterHook

       >>> hook = CounterHook()

       >>> event_a = auditor.create_event("event_a", hooks=[hook])

       >>> event_b = auditor.create_event("event_b", hooks=[hook])

       >>> with auditor.start_auditing(log_results=True):
       ...     for _ in range(15):
       ...         auditor.raise_event("event_a")
       ...     for _ in range(8):
       ...         auditor.raise_event("event_b")
       (INFO) seagrass: Calls to events recorded by CounterHook:
       (INFO) seagrass:     event_a: 15
       (INFO) seagrass:     event_b: 8
    """

    event_counter: t.Counter[str]

    def __init__(self) -> None:
        self.event_counter = Counter()

    def prehook(
        self, event_name: str, args: t.Tuple[t.Any, ...], kwargs: t.Dict[str, t.Any]
    ) -> None:
        self.event_counter[event_name] += 1

    def reset(self) -> None:
        self.event_counter.clear()

    def log_results(self, logger: logging.Logger) -> None:
        if len(self.event_counter) == 0:
            with HookContext("CounterHook", {}):
                logger.warning("no events recorded by counter")
            return

        for event in sorted(self.event_counter):
            ctx = {"event": event, "count": self.event_counter[event]}
            with HookContext("CounterHook", ctx):
                logger.info("CounterHook results")
