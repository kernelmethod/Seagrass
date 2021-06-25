# flake8: noqa: F401

# Type annotations for Seagrass
# Seagrass code should import type annotations from this module rather
# than from `typing` to ensure version compatibility

import sys
import typing

if sys.version_info < (3, 8):
    import typing_extensions as t_ext

    typing.Final = t_ext.Final
    typing.Protocol = t_ext.Protocol
    typing.runtime_checkable = t_ext.runtime_checkable

from typing import (
    Any,
    Callable,
    Counter,
    ContextManager,
    DefaultDict,
    Dict,
    Final,
    Iterator,
    List,
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
