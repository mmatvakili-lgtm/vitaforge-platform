import pytest
from safety_core import jsonlogic as J
from safety_core.errors import RuleError

D = {"a": 5, "s": "x", "n": {"k": 2}, "l": [1, 2]}


@pytest.mark.parametrize("logic,exp", [
    ({"var": "a"}, 5), ({"var": ["zz", 9]}, 9), ({"var": "zz"}, None), ({"var": "n.k"}, 2), ({"var": "a.b"}, None),
    ({"==": [{"var": "a"}, 5]}, True), ({"!=": [{"var": "a"}, 5]}, False),
    ({">": [{"var": "a"}, 4]}, True), ({">=": [{"var": "a"}, 5]}, True),
    ({"<": [{"var": "a"}, 5]}, False), ({"<=": [{"var": "a"}, 5]}, True),
    ({"in": [2, {"var": "l"}]}, True), ({"in": ["q", {"var": "l"}]}, False),
    ({"and": [True, {"==": [1, 1]}]}, True), ({"or": [False, False]}, False),
    ({"!": [True]}, False), ({"not": False}, True), (7, 7),
    ({">": [{"var": "s"}, 1]}, False), ({"<": [None, 1]}, False),
])
def test_ops(logic, exp):
    assert J.apply(logic, D) == exp


@pytest.mark.parametrize("bad", [{"eval": [1]}, {"a": 1, "b": 2}, {}])
def test_bad(bad):
    with pytest.raises(RuleError):
        J.apply(bad, D)
