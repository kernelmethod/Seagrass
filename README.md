# Seagrass

[![PyPI package version](https://img.shields.io/pypi/v/seagrass.svg)](https://pypi.org/project/seagrass)
[![Docs](https://readthedocs.org/projects/seagrass/badge/?version=latest)](https://seagrass.readthedocs.io/en/latest/?badge=latest)
[![Build status](https://github.com/kernelmethod/Seagrass/actions/workflows/CI.yml/badge.svg?branch=main)](https://github.com/kernelmethod/Seagrass/actions/workflows/CI.yml/)

*A Python event auditing and profiling multitool*

Seagrass is a library providing fast, pluggable hooks for instrumenting Python
code.

## Installation

You can install the latest version of Seagrass using `pip`:

```
pip install seagrass
```

## Introduction

At a low level, Seagrass is just a wrapper around Python's [context
managers](https://docs.python.org/3/glossary.html#term-context-manager) and
[function decorators](https://docs.python.org/3/glossary.html#term-decorator).
Working in conjunction, these two features make it possible to instrument and
attach context to arbitrary functions and blocks of code. However, at the far
end it can be tedious to have to manage, configure, and toggle code hooks using
just the standard library.

Seagrass provides a framework for developing hot-swappable hooks and managing
them at scale. For instance, suppose you wanted to count the number of times a
function was entered and see how much time was spent in it. You could use
Seagrass's built-in `CounterHook` and `TimerHook` as follows:

```python
import seagrass
from seagrass import Auditor
from seagrass.hooks import CounterHook, TimerHook

auditor = Auditor()
hooks = [CounterHook(), TimerHook()]

@auditor.audit(seagrass.auto, hooks=hooks)
def some_function_i_want_to_audit():
    ...

with auditor.start_auditing(log_results=True):
    some_function_i_want_to_audit()
```

Alternatively, you could use the `ProfilerHook` hook to get finer-grained
performance statistics based on Python's
[`cProfile`](https://docs.python.org/3/library/profile.html#module-cProfile)
module.

Seagrass really starts to shine once you start [writing your own
hooks](https://seagrass.readthedocs.io/en/stable/custom_hooks.html) through the
`ProtoHook` interface, or using one of the lightly-configurable hooks such as
[`LoggingHook`](https://seagrass.readthedocs.io/en/stable/api/seagrass.hooks.html#seagrass.hooks.LoggingHook)
or
[`ContextManagerHook`](https://seagrass.readthedocs.io/en/stable/api/seagrass.hooks.html#seagrass.hooks.ContextManagerHook).
You can write one set of hooks that transfer across multiple projects and toggle
them on-demand, filter them by event name, attach logging context with them, and
so on.

Check out the [quickstart
tutorial](https://seagrass.readthedocs.io/en/latest/quickstart.html) for a
longer crash course on using Seagrass.

## Documentation

The full documentation for Seagrass is available on ReadTheDocs:
https://seagrass.readthedocs.io/en/stable/

