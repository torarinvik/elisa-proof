"""Forged certificates must not use the opaque float literal token to prove IEEE-false laws."""
import copy

from portable_replay_support import *

package = export("float_literal_guard")
theorem = next(t for t in package["theorems"] if t["rule"] == "goal")
code, result = replay(package, "float-literal-baseline")
assert code == 0 and result["status"] == "replayed", result
# The deadzone type markers stay as hypotheses: they witness `deadzone` as a primitive scalar.
markers = [h for h in theorem["hypotheses"] if package["kernel"]["nodes"][h]["kind"] == "call"]
deadzone = next(i for i, n in enumerate(package["kernel"]["nodes"])
                if n["kind"] == "ident" and n["name"] == "deadzone")


def forge(name, build, accepted=False):
    forged = copy.deepcopy(package)
    hypotheses, conclusion = build(forged)
    claim = with_theorem(forged, dict(theorem, hypotheses=markers + hypotheses, conclusion=conclusion))
    reseal(claim, claim["theorems"][0])
    code, result = replay(claim, name)
    if accepted:
        assert code == 0 and result["status"] == "replayed", (name, result)
    else:
        assert code != 0 and result["status"] != "replayed", (name, result)
    return result


def lit(p, spelling):
    return append_node(p, "opaque-float-literal", name=spelling)


def cmp(p, op, left, right):
    return append_node(p, "binary", op, left, right)


def neg(p, root):
    return append_node(p, "unary", "not", root)


def either(p, left, right):
    return append_node(p, "binary", "or", left, right)


# NaN: reflexivity of a float variable is false.
forge("float-nan-reflexive", lambda p: ([], cmp(p, "==", deadzone, deadzone)))
# Distinct spellings of one value are equal; a syntactic disequality would be false.
forge("float-spelling-disequality",
      lambda p: ([], neg(p, cmp(p, "==", lit(p, "0.0"), lit(p, "0.00")))))
# Literal-to-literal comparisons carry no law the kernel may evaluate.
forge("float-literal-reflexive", lambda p: ([], cmp(p, "==", lit(p, "0.0"), lit(p, "0.0"))))
forge("float-literal-order", lambda p: ([], neg(p, cmp(p, "<", lit(p, "1.0"), lit(p, "0.5")))))
# Signed zero: x == 0.0 does not make x == -0.0 false.
forge("float-signed-zero",
      lambda p: ([cmp(p, "==", deadzone, lit(p, "0.0"))],
                 neg(p, cmp(p, "==", deadzone, append_node(p, "unary", "-", lit(p, "0.0"))))))
# Ordering is not total: not (x < 0.0) does not give x >= 0.0, nor trichotomy.
forge("float-negated-order",
      lambda p: ([neg(p, cmp(p, "<", deadzone, lit(p, "0.0")))], cmp(p, ">=", deadzone, lit(p, "0.0"))))
forge("float-trichotomy",
      lambda p: ([], either(p, cmp(p, "<", deadzone, lit(p, "0.0")),
                            either(p, cmp(p, "==", deadzone, lit(p, "0.0")),
                                   cmp(p, ">", deadzone, lit(p, "0.0"))))))
# Rounding: 16777217.0 and 16777216.0 are one f32, so x == a does not refute x == b.
forge("float-literal-rounding",
      lambda p: ([cmp(p, "==", deadzone, lit(p, "16777217.0"))],
                 neg(p, cmp(p, "==", deadzone, lit(p, "16777216.0")))))
# Arithmetic on the token is not a term.
forge("float-literal-arithmetic",
      lambda p: ([], cmp(p, "==", append_node(p, "binary", "+", deadzone, lit(p, "0.0")), deadzone)))
# Substitution through equality: x == 0.0 holds for -0.0, where 1.0 / x differs.
forge("float-substitution",
      lambda p: ([cmp(p, "==", deadzone, lit(p, "0.0"))],
                 cmp(p, "==", append_node(p, "binary", "/", lit(p, "1.0"), deadzone),
                     append_node(p, "binary", "/", lit(p, "1.0"), lit(p, "0.0")))))
# A literal beside an integer operand, with a numeric value, or with no spelling is malformed.
forge("float-literal-int-partner",
      lambda p: ([], neg(p, cmp(p, "==", append_node(p, "int", value="1"), lit(p, "1.0")))))
forge("float-literal-value-field",
      lambda p: ([], cmp(p, "<", deadzone, append_node(p, "opaque-float-literal", value="1", name="1.0"))))
forge("float-literal-empty",
      lambda p: ([], neg(p, cmp(p, "<", deadzone, append_node(p, "opaque-float-literal", name="")))))
# A literal as a bare proposition, outside a comparison.
forge("float-literal-bare", lambda p: ([], lit(p, "1.0")))
# Control: the exported theorem's own proof, with its atom rewritten to a literal comparison,
# still replays. This keeps every refusal above from passing only because literals never replay.
def literal_atom(p):
    nodes = p["kernel"]["nodes"]
    disjunction = nodes[theorem["conclusion"]]
    atom = cmp(p, "<", deadzone, lit(p, "0.0"))
    return [atom], either(p, disjunction["left"], neg(p, atom))


forge("float-literal-atom-control", literal_atom, accepted=True)
print("float literal forgery: IEEE-false certificates refused, literal atom control replays")
