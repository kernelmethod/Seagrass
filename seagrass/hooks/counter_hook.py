import typing as t
from collections import Counter
from seagrass.hooks import ProtoHook


class CounterHook(ProtoHook):

    event_counter: t.Counter[str]

    def __init__(self):
        self.event_counter = Counter()

    def prehook(
        self, event_name: str, args: t.Tuple[t.Any, ...], kwargs: t.Dict[str, t.Any]
    ) -> None:
        self.event_counter[event_name] += 1

    def reset(self):
        self.event_counter.clear()
