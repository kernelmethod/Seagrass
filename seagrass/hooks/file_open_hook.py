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
    __enabled: bool = False
    __current_event: t.Optional[str] = None

    def __init__(self):
        self.file_open_counter = defaultdict(t.Counter[FileOpenInfo])

        # Add the __sys_audit_hook closure as a new audit hook
        sys.addaudithook(self.__sys_audit_hook)

    def __sys_audit_hook(self, event, *args):
        try:
            if self.__enabled and event == "open":
                assert (
                    self.__current_event is not None
                ), "__current_event attribute has not been set"
                filename, mode, flags = args[0]

                info = FileOpenInfo(filename, mode, flags)
                self.file_open_counter[self.__current_event][info] += 1

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
        # Set __enabled so that we can enter the both of __sys_audit_hook
        self.__enabled = True
        self.__current_event = event_name

    def posthook(
        self,
        event_name: str,
        result: t.Any,
        context: None,
    ) -> None:
        self.__enabled = False
        self.__current_event = None

    def reset(self) -> None:
        self.file_open_counter.clear()

    def log_results(self, logger: logging.Logger) -> None:
        logger.info("%s results (file opened, count):", self.__class__.__name__)
        for (event, counter) in self.file_open_counter.items():
            logger.info("  event %s:", event)
            for (info, count) in counter.items():
                logger.info(
                    "    %s (mode=%s, flags=%s): opened %d times",
                    info.filename,
                    info.mode,
                    hex(info.flags),
                    count,
                )
