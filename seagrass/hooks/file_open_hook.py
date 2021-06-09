import logging
import sys
import typing as t
import warnings
from collections import defaultdict


class FileOpenInfo(t.NamedTuple):
    filename: str
    mode: str
    flags: int


class FileOpenHook:
    """An event hook for tracking calls to the Python standard
    library's `open` function."""

    # Give this hook slightly higher priority by default so that
    # we can avoid counting calls to open that occur in other
    # hooks.
    prehook_priority: int = 3
    posthook_priority: int = 3

    file_open_counter: t.DefaultDict[str, t.Counter[FileOpenInfo]]
    track_nested_opens: bool
    __current_event_stack: t.List[str]

    def __init__(self, track_nested_opens: bool = False) -> None:
        self.file_open_counter = defaultdict(t.Counter[FileOpenInfo])
        self.track_nested_opens = track_nested_opens
        self.__current_event_stack = []

        # Add the __sys_audit_hook closure as a new audit hook
        sys.addaudithook(self.__sys_audit_hook)

    def __sys_audit_hook(self, event: str, args: t.Tuple[t.Any, ...]) -> None:
        try:
            if len(self.__current_event_stack) > 0 and event == "open":
                filename, mode, flags = args
                info = FileOpenInfo(filename, mode, flags)

                # When track_nested_opens is set, we increment the number of opens
                # for every (unique) event in the __current_event_stack. Otherwise,
                # we only count it for the most recent event.
                if self.track_nested_opens:
                    for event in set(self.__current_event_stack):
                        self.file_open_counter[event][info] += 1
                else:
                    event = self.__current_event_stack[-1]
                    self.file_open_counter[event][info] += 1

        except Exception as ex:
            # In theory we shouldn't reach this point, but if we don't include
            # this try-catch block then we could hit an infinite loop if an
            # error *does* occur.
            warnings.warn(
                f"{ex.__class__.__name__} raised while calling {self.__class__.__name__}'s audit hook: {ex}"
            )

    def prehook(
        self, event_name: str, args: t.Tuple[t.Any, ...], kwargs: t.Dict[str, t.Any]
    ) -> None:
        self.__current_event_stack.append(event_name)

    def posthook(
        self,
        event_name: str,
        result: t.Any,
        context: None,
    ) -> None:
        self.__current_event_stack.pop()

    def reset(self) -> None:
        self.file_open_counter.clear()

    def log_results(self, logger: logging.Logger) -> None:
        logger.info("%s results (file opened, count):", self.__class__.__name__)
        for event in sorted(self.file_open_counter):
            logger.info("  event %s:", event)
            for (info, count) in self.file_open_counter[event].items():
                logger.info(
                    "    %s (mode=%s, flags=%s): opened %d times",
                    info.filename,
                    info.mode,
                    hex(info.flags),
                    count,
                )
