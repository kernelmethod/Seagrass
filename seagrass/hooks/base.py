from typing import Any, Tuple, Dict, Protocol


class ProtoHook(Protocol):
    """Basic interface for the auditing hooks used by Seagrass."""

    def prehook(self, args: Tuple[Any, ...], kwargs: Dict[str, Any]):
        ...

    def posthook(self, result: Any):
        ...
