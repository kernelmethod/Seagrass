import inspect
import typing as t
from collections import Counter, defaultdict


class TracedFrame(t.NamedTuple):
    """A NamedTuple that stores frame information collected from stack
    traces. We have to use this in place of storing FrameInfo references
    since doing so can create reference cycles; see
    https://docs.python.org/3/library/inspect.html#the-interpreter-stack
    """

    filename: str
    lineno: int

    @classmethod
    def from_frame_info(cls, frame: inspect.FrameInfo) -> "TracedFrame":
        return TracedFrame(frame.filename, frame.lineno)

    def __str__(self) -> str:
        return f"{self.filename}#{self.lineno}"


class StackTraceHook:
    """An audit hook that captures the stack trace of where events are raised
    and collects statistics about caller locations."""

    stack_depth: t.Optional[int]
    stack_trace_counter: t.DefaultDict[str, t.Counter[t.Tuple[TracedFrame, ...]]]

    def __init__(self, stack_depth: t.Optional[int] = 10) -> None:
        self.stack_depth = stack_depth
        self.stack_trace_counter = defaultdict(Counter)

    def prehook(
        self, event: str, args: t.Tuple[t.Any, ...], kwargs: t.Dict[str, t.Any]
    ) -> None:
        current_stack = inspect.stack()

        try:
            stack_depth = (
                len(current_stack) if self.stack_depth is None else self.stack_depth
            )
            frames = tuple(
                TracedFrame.from_frame_info(f) for f in current_stack[:stack_depth]
            )
            self.stack_trace_counter[event][frames] += 1
        finally:
            # See note in https://docs.python.org/3/library/inspect.html#the-interpreter-stack
            del current_stack

    def posthook(self, event: str, result: t.Any, context: None) -> None:
        # Posthook does nothing
        pass

    def reset(self) -> None:
        self.stack_trace_counter.clear()
