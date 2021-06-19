import typing as t
from collections import defaultdict
from logging import Logger
from .runtime_audit_hook import RuntimeAuditHook


class FileOpenInfo(t.NamedTuple):
    filename: str
    mode: str
    flags: int


class FileOpenHook(RuntimeAuditHook):
    """An event hook for tracking calls to the Python standard
    library's `open` function."""

    # Give this hook slightly higher priority by default so that
    # we can avoid counting calls to open that occur in other
    # hooks.
    prehook_priority: int = 3
    posthook_priority: int = 3

    file_open_counter: t.DefaultDict[str, t.Counter[FileOpenInfo]]

    def __init__(self) -> None:
        super().__init__()
        self.file_open_counter = defaultdict(t.Counter[FileOpenInfo])

    def sys_hook(self, runtime_event: str, args: t.Tuple[t.Any, ...]) -> None:
        if runtime_event == "open" and self.current_event is not None:
            filename, mode, flags = args
            info = FileOpenInfo(filename, mode, flags)
            self.file_open_counter[self.current_event][info] += 1

    def reset(self) -> None:
        self.file_open_counter.clear()

    def log_results(self, logger: Logger) -> None:
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
