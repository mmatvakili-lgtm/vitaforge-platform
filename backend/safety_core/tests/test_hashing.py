import re
from safety_core.hashing import decision_id_from_hash, inputs_hash
from .conftest import make_ex


def test_id_shape_and_stability():
    h = "a" * 64
    assert decision_id_from_hash(h) == decision_id_from_hash(h)
    assert re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", decision_id_from_hash(h))


def test_hash_ignores_mapping_order(req):
    a = req(red_flag_answers={"chest_pain": False, "fainting": False})
    b = req(red_flag_answers={"fainting": False, "chest_pain": False})
    assert inputs_hash(a, 1) == inputs_hash(b, 1)
    assert inputs_hash(a, 1) != inputs_hash(a, 2)
