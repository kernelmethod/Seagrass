import seagrass._typing as _t
from contextvars import ContextVar, Token

current_hook_ctx: ContextVar["HookContext"] = ContextVar("seagrass_hook_ctx")

if _t.TYPE_CHECKING:
    import sys

    if sys.version_info >= (3, 9):
        CtxType = Token["HookContext"]
    else:
        CtxType = Token


class HookContext:
    """Logging context provided by a hook that gets attached to logs."""

    __slots__ = ["name", "args", "previous_ctx"]

    name: str
    args: _t.Dict[str, _t.Any]
    previous_ctx: _t.Optional["CtxType"]

    def __init__(self, name: str, args: _t.Dict[str, _t.Any]) -> None:
        """Create a new ``HookContext`` instance."""

        self.name = name
        self.args = args
        self.previous_ctx = None

    def __enter__(self) -> "HookContext":
        self.previous_ctx = current_hook_ctx.set(self)
        return self

    def __exit__(self, *args) -> None:
        if self.previous_ctx is not None:
            current_hook_ctx.reset(self.previous_ctx)
        self.previous_ctx = None


T = _t.TypeVar("T")


@_t.overload
def get_hook_context() -> HookContext:
    ...  # pragma: no cover


@_t.overload
def get_hook_context(default: T) -> _t.Union[HookContext, T]:
    ...  # pragma: no cover


def get_hook_context(default: _t.Maybe[T] = _t.MISSING) -> _t.Union[HookContext, T]:
    """Retrieve the logging context provided by an executing hook.

    :raises LookupError: if no hook is currently being executed, and ``default`` is not
        specified.
    """
    if isinstance(default, _t.Missing):
        return current_hook_ctx.get()
    else:
        return current_hook_ctx.get(default)
