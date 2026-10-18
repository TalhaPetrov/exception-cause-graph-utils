"""Core implementation for walking exception cause and context chains."""

import traceback as _traceback


def _format_traceback(exc):
    """Return the traceback string for *exc* or an empty string.

    `traceback.format_exception` lists the cause/context chain itself via
    its own internal traversal. We do NOT want that: the caller already
    receives the chain in order, so duplicating it inside each entry's
    traceback field would be noisy and recursive in presentation. We pass
    only the leaf exception to format_exception so the string covers this
    single exception's immediate traceback.
    """
    if exc.__traceback__ is None:
        return ""
    lines = _traceback.format_exception(type(exc), exc, exc.__traceback__)
    return "".join(lines)


def _walk(exc, depth):
    """Generator yielding (exc, depth, relationship) tuples.

    Python's `__cause__` / `__context__` chain can form cycles in extreme
    cases (an exception whose __context__ points back to a parent). We
    guard with an id-set so the walk terminates. Because we also dedupe
    a node from multiple parents, a given exception object appears at most
    once in the output at its first (shallowest) encounter.
    """
    seen = set()
    queue = [(exc, depth, "root")]
    while queue:
        current, cur_depth, relationship = queue.pop(0)
        if id(current) in seen:
            continue
        seen.add(id(current))
        yield (current, cur_depth, relationship)
        cause = current.__cause__
        context = current.__context__
        if cause is not None and id(cause) not in seen:
            queue.append((cause, cur_depth + 1, "cause"))
        if context is not None and id(context) not in seen:
            queue.append((context, cur_depth + 1, "context"))


def walk_exception_chain(exc):
    """Walk the __cause__ and __context__ chain of an exception.

    Returns a flat list of dictionaries, each containing:
      - type:        the exception class object
      - type_name:   fully-qualified type name as "module.QualName"
      - message:     str(exc)
      - traceback:   formatted traceback string for this exception only
      - depth:       0 for the root, increments per link
      - relationship: 'root' for the input, 'cause' or 'context' otherwise

    The traversal is a breadth-first walk that prefers __cause__ over
    __context__ at each node, mirroring how `traceback` prints chains.
    An exception object appears at most once to guarantee termination even
    when the chain contains a cycle.
    """
    if not isinstance(exc, BaseException):
        raise TypeError(
            "walk_exception_chain expects a BaseException instance, got %s" % type(exc).__name__
        )
    result = []
    for current, depth, relationship in _walk(exc, 0):
        type_name = "%s.%s" % (type(current).__module__, type(current).__qualname__)
        result.append({
            "type": type(current),
            "type_name": type_name,
            "message": str(current),
            "traceback": _format_traceback(current),
            "depth": depth,
            "relationship": relationship,
        })
    return result
