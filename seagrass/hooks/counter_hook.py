from collections import Counter
from seagrass.hooks import ProtoHook
from typing import Any, Tuple, Dict


class CounterHook(ProtoHook):

    event_counter: Counter = Counter()

    def prehook(
        self, event_name: str, args: Tuple[Any, ...], kwargs: Dict[str, Any]
    ) -> None:
        self.event_counter[event_name] += 1

    def reset(self):
        self.event_counter.clear()
