# flake8: noqa: F401
import typing as t
from .auditor import Auditor, get_audit_logger, DEFAULT_LOGGER_NAME

# "Global auditor" that can be used to audit events without having to create an
# auditor first.
__GLOBAL_AUDITOR: t.Final[Auditor] = Auditor()

def global_auditor() -> Auditor:
    return __GLOBAL_AUDITOR

# Export the external API of the global Auditor instance from the module
audit = global_auditor().audit
create_event = global_auditor().create_event
raise_event = global_auditor().raise_event
toggle_event = global_auditor().toggle_event
toggle_auditing = global_auditor().toggle_auditing
start_auditing = global_auditor().start_auditing
add_hooks = global_auditor().add_hooks
reset_hooks = global_auditor().reset_hooks
log_results = global_auditor().log_results

__all__ = [
    "Auditor",
    "get_audit_logger",
    "global_auditor",
    "audit",
    "create_event",
    "raise_event",
    "toggle_event",
    "toggle_auditing",
    "start_auditing",
    "add_hooks",
    "reset_hooks",
    "log_results",
]
