# flake8: noqa: F401

# Type annotations for Seagrass
# Seagrass code should import type annotations from this module rather
# than from `typing` to ensure version compatibility

from sys import version_info as _version_info
from typing import *

# The __all__ list includes all of the attributes of typing that were
# brought into scope.
import typing as _t

__all__: List[str] = []
__all__ += _t.__all__  # type: ignore[attr-defined]

# Import additional attributes for Python < 3.8
_extended_attrs = ["Final", "Literal", "Protocol", "runtime_checkable"]

if _version_info < (3, 8):
    import typing_extensions as _t_ext

    for attr in filter(lambda attr: attr not in __all__, _extended_attrs):
        # Dynamically bring the attribute into scope by updating the globals
        # dictionary
        globals().update({attr: getattr(_t_ext, attr)})
        __all__.append(attr)

# Additional types for Seagrass:
class Missing:
    """Unique type used throughout Seagrass to represent a missing value."""

    __slots__: List[str] = []

    def __repr__(self) -> str:
        return f"<{__name__}.{self.__class__.__name__}>"


MISSING: Final[Missing] = Missing()

_T = TypeVar("_T")

# Maybe[T] is a type that represents a value that is potentially missing its value.
# This is distinct from Optional[T], which represents a value that could have type
# T or that could be None. In cases where a None value should be allowed, this type
# may be used instead.
Maybe = Union[_T, Missing]

_F = TypeVar("_F", bound=Callable)


class AuditedFunc(Protocol[_F]):
    __event_name__: str
    __call__: _F


class AuditDecorator(Protocol[_F]):
    @property
    def __call__(self) -> Callable[[_F], AuditedFunc[_F]]:
        ...


# Add additional types to the __all__ list:

__all__ += [
    "Missing",
    "MISSING",
    "Maybe",
    "AuditedFunc",
    "AuditDecorator",
]

__all__ = sorted(__all__)
