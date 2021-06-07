# Seagrass

[![PyPI package version](https://img.shields.io/pypi/v/seagrass.svg)](https://pypi.org/project/seagrass)
[![Python versions](https://img.shields.io/pypi/pyversions/seagrass.svg)](https://pypi.org/project/seagrass)
![Build status](https://github.com/kernelmethod/Seagrass/actions/workflows/CI.yml/badge.svg?branch=main)

*A Python event auditing and profiling multitool*

Seagrass is a Python library for hooking and auditing events in your Python
code.

## Examples

Here is a simple example of using Seagrass to audit the number of times we call
two example functions, `add` and `sub`:

```python
import logging
from seagrass import Auditor
from seagrass.hooks import CounterHook

# Preliminary: configure logging
fh = logging.StreamHandler()
fh.setLevel(logging.INFO)
formatter = logging.Formatter("%(name)s: %(message)s")
fh.setFormatter(formatter)

logger = logging.getLogger("seagrass")
logger.setLevel(logging.INFO)
logger.addHandler(fh)

# Create a new Auditor instance
auditor = Auditor()

# Create a hook that will count each time an event occurs
hook = CounterHook()

# Now define some new events by hooking some example functions
@auditor.decorate("event.add", hooks=[hook])
def add(x: int, y: int) -> int:
    return x + y

@auditor.decorate("event.sub", hooks=[hook])
def sub(x: int, y: int) -> int:
    return x - y

# Now start auditing!
with auditor.audit():
    add(1, 2)
    add(3, 4)
    sub(5, 2)

# Display the results of auditing. This should produce the following output:
#
#    seagrass: Calls to events recorded by CounterHook:
#    seagrass:     event.add: 2
#    seagrass:     event.sub: 1
#
auditor.log_results()
```

From there we can perform more complex tasks. For instance, here's an example
where we override Python's `time.sleep` and profile it:

```python
import time
from seagrass import Auditor
from seagrass.hooks import CounterHook, ProfilerHook

# Omitted: logging configuration

auditor = Auditor()
hooks = [CounterHook(), ProfilerHook()]

ausleep = auditor.wrap(time.sleep, "time.sleep", hooks=hooks)
setattr(time, "sleep", ausleep)

with auditor.audit():
    for _ in range(20):
        time.sleep(0.1)

auditor.log_results()
```

You can also define custom auditing hooks by creating a new class that
implements the interface defined by `seagrass.base.ProtoHook`. In the example
below, we define a custom hook that raises an `AssertionError` if the argument
to the function `say_hello` has the wrong type.

```python
from seagrass import Auditor

auditor = Auditor()

class MyTypeCheckHook:

    prehook_priority: int = 0
    posthook_priority: int = 0

    def prehook(self, event_name, args, kwargs):
        assert isinstance(args[0], str)

    def posthook(self, event_name, result, context):
        pass

    def reset(self):
        pass

hook = MyTypeCheckHook()

@auditor.decorate("event.say_hello", hooks=[hook])
def say_hello(name: str):
    return f"Hello, {name}!"

# Outside of an auditing context, the hook doesn't get called. The
# following calls to say_hello will both return without error, even
# though the second one uses the wrong argument type.
say_hello("Alice")
say_hello(1)

# Inside of an auditing context, the hooks will get called.
with auditor.audit():
    say_hello("Bob")
    # This call to say_hello will raise an AssertionError
    say_hello(2)
```
