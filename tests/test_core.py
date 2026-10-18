import unittest

from exception_cause_graph_utils import walk_exception_chain
from exception_cause_graph_utils.core import walk_exception_chain as core_walk


class TestWalkExceptionChain(unittest.TestCase):

    def test_module_exports_match(self):
        self.assertIs(walk_exception_chain, core_walk)

    def test_simple_exception(self):
        exc = ValueError("boom")
        chain = walk_exception_chain(exc)
        self.assertEqual(len(chain), 1)
        entry = chain[0]
        self.assertIs(entry["type"], ValueError)
        self.assertEqual(entry["message"], "boom")
        self.assertEqual(entry["depth"], 0)
        self.assertEqual(entry["relationship"], "root")
        self.assertEqual(entry["traceback"], "")
        self.assertIn("ValueError", entry["type_name"])

    def test_cause_chain(self):
        inner = ValueError("inner")
        try:
            raise RuntimeError("outer") from inner
        except RuntimeError as e:
            exc = e
        chain = walk_exception_chain(exc)
        self.assertEqual(len(chain), 2)
        self.assertEqual(chain[0]["message"], "outer")
        self.assertEqual(chain[0]["depth"], 0)
        self.assertEqual(chain[0]["relationship"], "root")
        self.assertEqual(chain[1]["message"], "inner")
        self.assertEqual(chain[1]["depth"], 1)
        self.assertEqual(chain[1]["relationship"], "cause")
        self.assertIs(chain[1]["type"], ValueError)

    def test_context_chain(self):
        inner = KeyError("missing")
        outer = None
        try:
            try:
                raise inner
            except KeyError:
                outer = RuntimeError("wrapped")
                raise outer
        except RuntimeError as e:
            exc = e
        chain = walk_exception_chain(exc)
        self.assertEqual(len(chain), 2)
        self.assertEqual(chain[0]["message"], "wrapped")
        self.assertEqual(chain[0]["relationship"], "root")
        self.assertEqual(chain[1]["message"], "'missing'")
        self.assertEqual(chain[1]["relationship"], "context")
        self.assertEqual(chain[1]["depth"], 1)
        self.assertIs(chain[1]["type"], KeyError)

    def test_cause_preferred_over_context(self):
        cause = ValueError("explicit cause")
        context = KeyError("implicit context")
        outer = RuntimeError("outer")
        outer.__cause__ = cause
        outer.__context__ = context
        chain = walk_exception_chain(outer)
        self.assertEqual(len(chain), 3)
        self.assertEqual(chain[0]["relationship"], "root")
        self.assertEqual(chain[1]["relationship"], "cause")
        self.assertEqual(chain[1]["message"], "explicit cause")
        self.assertEqual(chain[2]["relationship"], "context")
        self.assertEqual(chain[2]["message"], "'implicit context'")

    def test_diamond_dedup(self):
        """A node reachable as both cause and context of different parents
        must appear only once, at its shallowest depth."""
        shared = ValueError("shared")
        mid = RuntimeError("mid")
        mid.__cause__ = shared
        top = TypeError("top")
        top.__cause__ = mid
        top.__context__ = shared
        chain = walk_exception_chain(top)
        messages = [e["message"] for e in chain]
        self.assertEqual(messages.count("shared"), 1)
        shared_entry = next(e for e in chain if e["message"] == "shared")
        self.assertEqual(shared_entry["depth"], 1)
        self.assertEqual(shared_entry["relationship"], "context")

    def test_cycle_termination(self):
        a = RuntimeError("a")
        b = ValueError("b")
        a.__context__ = b
        b.__context__ = a
        chain = walk_exception_chain(a)
        messages = [e["message"] for e in chain]
        self.assertEqual(messages, ["a", "b"])

    def test_traceback_present_when_raised(self):
        try:
            raise ValueError("raised")
        except ValueError as e:
            exc = e
        chain = walk_exception_chain(exc)
        self.assertEqual(len(chain), 1)
        tb = chain[0]["traceback"]
        self.assertIsInstance(tb, str)
        self.assertIn("Traceback", tb)
        self.assertIn("ValueError: raised", tb)

    def test_type_name_includes_module(self):
        exc = ValueError("x")
        chain = walk_exception_chain(exc)
        self.assertTrue(chain[0]["type_name"].endswith("ValueError"))
        self.assertIn(".", chain[0]["type_name"])

    def test_non_exception_rejected(self):
        with self.assertRaises(TypeError):
            walk_exception_chain("not an exception")
        with self.assertRaises(TypeError):
            walk_exception_chain(None)

    def test_nested_cause_and_context(self):
        deep = ValueError("deep")
        mid = TypeError("mid")
        mid.__cause__ = deep
        outer = RuntimeError("outer")
        outer.__context__ = mid
        chain = walk_exception_chain(outer)
        self.assertEqual(len(chain), 3)
        self.assertEqual(chain[0]["relationship"], "root")
        self.assertEqual(chain[1]["relationship"], "context")
        self.assertEqual(chain[1]["message"], "mid")
        self.assertEqual(chain[2]["relationship"], "cause")
        self.assertEqual(chain[2]["message"], "deep")
        self.assertEqual(chain[2]["depth"], 2)

    def test_return_type_is_list_of_dicts(self):
        chain = walk_exception_chain(ValueError("x"))
        self.assertIsInstance(chain, list)
        self.assertIsInstance(chain[0], dict)
        for key in ("type", "type_name", "message", "traceback", "depth", "relationship"):
            self.assertIn(key, chain[0])

    def test_depth_increments_correctly(self):
        c = ValueError("c")
        b = TypeError("b")
        b.__cause__ = c
        a = RuntimeError("a")
        a.__cause__ = b
        chain = walk_exception_chain(a)
        depths = [e["depth"] for e in chain]
        self.assertEqual(depths, [0, 1, 2])


if __name__ == "__main__":
    unittest.main()
