import logging
import sys
import typing as t
import warnings


class FileOpenHook:
    """An event hook for tracking calls to the Python standard
    library's `open` function."""

    # Give this hook slightly higher priority by default so that
    # we can avoid counting calls to open that occur in other
    # hooks.
    prehook_priority: int = 3
    posthook_priority: int = 3

    # Boolean variables that indicate whether we should track the
    # mode that files were opened with, and whether we should track
    # the flags those files were opened with.
    track_mode: bool
    track_flags: bool

    file_open_counter: t.Counter[str]
    __enabled: bool = False

    def __init__(self, track_mode: bool = True, track_flags: bool = False):
        self.file_open_counter = t.Counter[str]()
        self.track_mode = track_mode
        self.track_flags = track_flags

        # Add the __sys_audit_hook closure as a new audit hook
        sys.addaudithook(self.__sys_audit_hook)

    def __sys_audit_hook(self, event, *args):
        try:
            if self.__enabled and event == "open":
                filename, mode, flags = args[0]

                # Create a key for the file_open_counter that we will increment
                key = filename
                if self.track_mode:
                    key += f" (mode='{mode}')"
                if self.track_flags:
                    key += f" (flags='{hex(flags)}')"

                self.file_open_counter[key] += 1

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

    def posthook(
        self,
        event_name: str,
        result: t.Any,
        context: None,
    ) -> None:
        self.__enabled = False

    def reset(self) -> None:
        self.file_open_counter.clear()

    def log_results(self, logger: logging.Logger) -> None:
        logger.info("%s results (file opened, count):", self.__class__.__name__)
        for (key, count) in self.file_open_counter.items():
            logger.info("    %s: %d", key, count)
