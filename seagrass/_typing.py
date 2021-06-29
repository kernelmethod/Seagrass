# flake8: noqa: F401

# Type annotations for Seagrass
# Seagrass code should import type annotations from this module rather
# than from `typing` to ensure version compatibility

import sys
import typing as t

if sys.version_info < (3, 8):
    import typing_extensions as t_ext

    t.Final = t_ext.Final
    t.Literal = t_ext.Literal
    t.Protocol = t_ext.Protocol
    t.runtime_checkable = t_ext.runtime_checkable

from typing import (
    Any,
    Callable,
    Counter,
    ContextManager,
    DefaultDict,
    Dict,
    Final,
    Generic,
    Iterator,
    List,
    Literal,
    NamedTuple,
    Optional,
    Protocol,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
    runtime_checkable,
)

# Unique type used throughout Seagrass to represent a missing value


class Missing:
    __slots__: t.List[str] = []

    def __repr__(self) -> str:
        return f"<seagrass._typing.{self.__class__.__name__}"


MISSING: t.Final[Missing] = Missing()

T = t.TypeVar("T")

# Maybe[T] is a type that represents a value that is potentially missing its value.
# This is distinct from Optional[T], which represents a value that could have type
# T or that could be None. In cases where a None value should be allowed, this type
# may be used instead.
Maybe = t.Union[T, Missing]

F = t.TypeVar("F", bound=t.Callable)


class AuditedFunc(t.Protocol[F]):
    __event_name__: str
    __call__: F


class AuditDecorator(t.Protocol[F]):
    @property
    def __call__(self) -> t.Callable[[F], AuditedFunc[F]]:
        ...
