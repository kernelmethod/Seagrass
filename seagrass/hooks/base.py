from typing import Any, Tuple, Dict, Protocol, TypeVar

# Type variable for contexts returned by prehooks
C = TypeVar("C")


class ProtoHook(Protocol[C]):
    """Interface for hooks that can be used by Seagrass."""

    # Priority in which prehooks and posthooks should be executed.
    #
    # - Prehooks with high priority are executed _after_
    #   hooks with a lower prehook_priority
    # - Posthooks with high priority are executed _before_
    #   hooks with lower posthook_priority
    #
    # This ensures that a ProtoHook whose prehook_priority and
    # posthook_priority are both high is likely to have its prehook
    # and posthook executed directly before and directly after the
    # execution of a wrapped event.
    prehook_priority: int = 0
    posthook_priority: int = 0

    def prehook(
        self, event_name: str, args: Tuple[Any, ...], kwargs: Dict[str, Any]
    ) -> C:
        """Run the prehook."""
        ...

    def posthook(self, event_name: str, result: Any, context: C):
        """Run the posthook."""
        ...

    def reset(self) -> None:
        """Resets the internal state of the hook (if there is any)."""
        ...
