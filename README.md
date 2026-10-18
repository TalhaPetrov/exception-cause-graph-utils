# exception-cause-graph-utils

Walks the `__cause__` and `__context__` chains of a Python exception instance and returns a flat list of dictionaries — each carrying the exception type, message, traceback string, depth, and relationship label (`root`, `cause`, or `context`).

```python
from exception_cause_graph_utils import walk_exception_chain

try:
    raise RuntimeError("outer") from ValueError("inner")
except RuntimeError as exc:
    for entry in walk_exception_chain(exc):
        print(entry["depth"], entry["relationship"], entry["type_name"], entry["message"])
    # 0 root builtins.RuntimeError outer
    # 1 cause builtins.ValueError inner
```

## Why this exists

`traceback.format_exception` prints the full cause/context chain as a single string, which is fine for humans but awkward when you need structured access to each exception in the chain — for logging, aggregation, or filtering. This library gives you that flat, ordered list so each exception's type, message, and traceback are individually addressable.

The key trade-off: at each node we prefer `__cause__` over `__context__` (matching CPython's own printing order) and do a breadth-first walk. An exception object that is reachable via multiple paths appears only once, at its shallowest depth, so the output never contains a cycle even if the live chain does.

## Edge case to know about

The `traceback` field of each entry contains only that single exception's immediate traceback — not the formatted tracebacks of its ancestors. This is deliberate: including the full nested chain inside each entry would duplicate information across entries and produce deeply recursive output. If you want the classic monolithic string, call `traceback.format_exception` on the root exception yourself.

Also note: an exception with no live traceback (constructed but never raised, or whose traceback was already cleared) yields an empty string in the `traceback` field, not `None`.
