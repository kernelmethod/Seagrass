import logging
import typing as t
from seagrass import get_audit_logger
from seagrass.base import ProtoHook

log_input_t = str
prehook_msg_t = t.Callable[[str, t.Tuple[t.Any, ...], t.Dict[str, t.Any]], log_input_t]
posthook_msg_t = t.Callable[[str, t.Any], log_input_t]


class LoggingHook(ProtoHook[None]):
    """A hook that emits a new log whenever it gets called."""

    loglevel: int
    prehook_msg: t.Optional[prehook_msg_t]
    posthook_msg: t.Optional[posthook_msg_t]

    def __init__(
        self,
        prehook_msg: t.Optional[prehook_msg_t] = None,
        posthook_msg: t.Optional[posthook_msg_t] = None,
        loglevel: int = logging.DEBUG,
    ) -> None:
        if prehook_msg is None and posthook_msg is None:
            raise ValueError(
                (
                    "At least one of the keyword arguments prehook_msg and posthook_msg "
                    "must be specified and not equal to None"
                )
            )

        self.prehook_msg = prehook_msg
        self.posthook_msg = posthook_msg
        self.loglevel = loglevel

    def prehook(
        self,
        event_name: str,
        args: t.Tuple[t.Any, ...],
        kwargs: t.Dict[str, t.Any],
    ) -> None:
        if self.prehook_msg is None:
            pass
        else:
            if (logger := get_audit_logger()) is not None:
                logger.log(self.loglevel, self.prehook_msg(event_name, args, kwargs))

    def posthook(
        self,
        event_name: str,
        result: t.Any,
        context: None,
    ) -> None:
        if self.posthook_msg is None:
            pass
        else:
            if (logger := get_audit_logger()) is not None:
                logger.log(self.loglevel, self.posthook_msg(event_name, result))
