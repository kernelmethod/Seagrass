import logging
import seagrass._typing as _t


class SeagrassLogFilter(logging.Filter):
    """A custom :py:class:`logging.Filter` that attaches contextual information
    about Seagrass events to logs."""

    def filter(self, record) -> bool:
        from seagrass.events import get_current_event
        from seagrass.hooks import get_hook_context

        seagrass_context: _t.Dict[str, _t.Any] = {}
        seagrass_context["event"] = get_current_event(default=None)

        if (hook_ctx := get_hook_context(default=None)) is not None:
            seagrass_context["hook"] = hook_ctx.name
            seagrass_context["hook_ctx"] = hook_ctx.args

        if hasattr(record, "seagrass"):
            record.seagrass = {**record.seagrass, **seagrass_context}
        else:
            record.seagrass = seagrass_context

        return True
