"""SMT quantifier oracle (BACKLOG W-05; design in docs/w05-quantifier-oracle.md).

Reads `quantifier_problem` records -- from the near misses of an `elisa-proof --json` report, or
a JSON file of problems with `--problems` -- and asks Z3, with E-matching only (MBQI off), to
refute each negated goal. On `unsat` it walks the proof for `quant-inst` steps and keeps each
instance whose term mentions only source names. The output is one hint record per goal,

    2 <goal_id> <count> (<fact_index> "<term>"){count}

Z3 is untrusted: the checker admits an instance only through the W-02 instance rule after it
proves the term lies in the fact's range, so a wrong instance only fails to prove, and replay
never needs Z3. The checker side is not implemented yet; this half is testable on its own.

Problem grammar (s-expressions): `(forall j lo hi body)` is `forall j in lo..<hi: body`;
`(select xs i)` is `xs[i]`; `(count xs)` is `xs.count`; operators `+ - * < <= > >= == != and or
not`; integer literals; names.

usage: quantifier_oracle.py [--hints-out FILE] (--problems FILE | <file.elisa>)
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
Z3 = os.environ.get("ELISA_PROOF_Z3", shutil.which("z3") or "z3")
TIMEOUT_MS = 2000
MAX_FACTS = 32
MAX_ARRAYS = 8
MAX_TERMS = 64
MAX_DEPTH = 12
MAX_INSTANCES = 8
MAX_TERM_DEPTH = 6
MAX_RECORD_BYTES = 4096
BINDER_PREFIX = "elisa_q"
OPERATORS = {"+": "+", "-": "-", "*": "*", "<": "<", "<=": "<=", ">": ">", ">=": ">=",
             "==": "=", "and": "and", "or": "or", "not": "not"}
NAME = re.compile(r"^[A-Za-z_][A-Za-z_0-9]*$")


sys.setrecursionlimit(20000)  # Z3 proofs nest deeply; parsing and expansion recurse.


class Malformed(Exception):
    pass


def parse(text):
    tokens = re.findall(r'\(|\)|"[^"]*"|[^\s()]+', text)
    position = 0

    def read():
        nonlocal position
        if position >= len(tokens):
            raise Malformed("unexpected end of expression")
        token = tokens[position]
        position += 1
        if token == "(":
            items = []
            while position < len(tokens) and tokens[position] != ")":
                items.append(read())
            if position >= len(tokens):
                raise Malformed("unclosed parenthesis")
            position += 1
            return items
        if token == ")":
            raise Malformed("unexpected )")
        return token

    value = read()
    if position != len(tokens):
        raise Malformed("trailing tokens")
    return value


def depth(expression):
    return 1 + max((depth(item) for item in expression), default=0) if isinstance(expression, list) else 1


def is_int(token):
    return isinstance(token, str) and re.fullmatch(r"-?[0-9]+", token) is not None


def smt_int(token):
    return f"(- {token[1:]})" if token.startswith("-") else token


def to_smt(expression, binders, arrays, names, fact_index=None):
    """Translate one problem expression. `binders` maps a source binder to its SMT name."""
    if isinstance(expression, str):
        if is_int(expression):
            return smt_int(expression)
        if expression in binders:
            return binders[expression]
        if not NAME.match(expression) or expression.startswith(BINDER_PREFIX):
            raise Malformed(f"bad name {expression!r}")
        if expression in arrays:
            raise Malformed(f"array {expression} used as a scalar")
        names.add(expression)
        return expression
    if not expression:
        raise Malformed("empty list")
    head, rest = expression[0], expression[1:]
    recurse = lambda item: to_smt(item, binders, arrays, names, None)
    if head == "forall":
        if len(rest) != 4 or not isinstance(rest[0], str) or not NAME.match(rest[0]):
            raise Malformed("forall needs a binder, two bounds and a body")
        if fact_index is None:
            raise Malformed("a quantifier is only accepted as a whole fact or goal")
        binder = f"{BINDER_PREFIX}{fact_index}"
        lower, upper = recurse(rest[1]), recurse(rest[2])
        body = to_smt(rest[3], {**binders, rest[0]: binder}, arrays, names, None)
        return (f"(forall (({binder} Int)) (=> (and (<= {lower} {binder}) (< {binder} {upper})) {body}))")
    if head == "select":
        if len(rest) != 2 or rest[0] not in arrays:
            raise Malformed("select needs a declared array and an index")
        return f"(select {rest[0]} {recurse(rest[1])})"
    if head == "count":
        if len(rest) != 1 or rest[0] not in arrays:
            raise Malformed("count needs a declared array")
        return f"{rest[0]}__count"
    if head == "!=":
        if len(rest) != 2:
            raise Malformed("!= is binary")
        return f"(not (= {recurse(rest[0])} {recurse(rest[1])}))"
    if head not in OPERATORS:
        raise Malformed(f"unknown operator {head!r}")
    if head == "not" and len(rest) != 1 or head != "not" and len(rest) < (1 if head == "-" else 2):
        raise Malformed(f"wrong arity for {head}")
    return f"({OPERATORS[head]} {' '.join(recurse(item) for item in rest)})"


def query(problem):
    """The SMT-LIB text for one problem and the source names it may mention."""
    facts = problem.get("facts", [])
    arrays = problem.get("arrays", [])
    if len(facts) > MAX_FACTS or len(arrays) > MAX_ARRAYS or len(problem.get("terms", [])) > MAX_TERMS:
        raise Malformed("problem over budget")
    if any(not isinstance(a, str) or not NAME.match(a) for a in arrays):
        raise Malformed("bad array name")
    names = set()
    asserted = []
    for fact in facts:
        expression = parse(fact["expr"])
        if depth(expression) > MAX_DEPTH:
            raise Malformed("fact too deep")
        asserted.append((fact["index"], to_smt(expression, {}, arrays, names, fact["index"])))
    goal = parse(problem["goal"])
    if depth(goal) > MAX_DEPTH:
        raise Malformed("goal too deep")
    goal_smt = to_smt(goal, {}, arrays, names, -1)
    lines = ["(set-option :produce-proofs true)", "(set-option :smt.mbqi false)",
             f"(set-option :timeout {TIMEOUT_MS})"]
    lines += [f"(declare-const {name} Int)" for name in sorted(names)]
    for array in arrays:
        lines += [f"(declare-const {array} (Array Int Int))", f"(declare-const {array}__count Int)",
                  f"(assert (<= 0 {array}__count))"]
    lines += [f"(assert {text})" for _, text in asserted]
    lines += [f"(assert (not {goal_smt}))", "(check-sat)", "(get-proof)"]
    return "\n".join(lines) + "\n", names | {f"{a}__count" for a in arrays}


def from_smt(term, names):
    """An SMT ground term back in problem grammar, or None if it mentions a non-source name."""
    if isinstance(term, str):
        if is_int(term):
            return term
        if term.endswith("__count") and term in names:
            return f"(count {term[:-len('__count')]})"
        return term if term in names else None
    if len(term) == 2 and term[0] == "-" and is_int(term[1]):
        return f"-{term[1]}" if not term[1].startswith("-") else term[1][1:]
    if not term or term[0] not in ("+", "-", "*", "select"):
        return None
    if term[0] == "select":
        if len(term) != 3 or not isinstance(term[1], str) or f"{term[1]}__count" not in names:
            return None
        parts = [term[1], from_smt(term[2], names)]
    else:
        parts = [from_smt(item, names) for item in term[1:]]
    if any(part is None for part in parts):
        return None
    return "(" + " ".join([term[0]] + parts) + ")"


def let_bindings(node, table):
    """Collect Z3's proof abbreviations (`(let ((@x1 ...) ($x2 ...)) body)`); their names are unique."""
    if not isinstance(node, list):
        return
    if len(node) == 3 and node[0] == "let" and isinstance(node[1], list):
        for binding in node[1]:
            if isinstance(binding, list) and len(binding) == 2 and isinstance(binding[0], str):
                table[binding[0]] = binding[1]
    for item in node:
        let_bindings(item, table)


def expand(node, table, budget=20000):
    """`node` with abbreviations replaced, or None past `budget` nodes (shared terms can blow up)."""
    count = 0

    def go(item):
        nonlocal count
        count += 1
        if count > budget:
            raise OverflowError
        if isinstance(item, str):
            return go(table[item]) if item in table else item
        return [go(child) for child in item]

    try:
        return go(node)
    except (OverflowError, RecursionError):
        return None


def instances(proof, names):
    """(fact_index, term) pairs from every `(_ quant-inst t)` step on a source quantifier."""
    table = {}
    let_bindings(proof, table)
    found = []

    def walk(node):
        if not isinstance(node, list):
            return
        # ((_ quant-inst t) (or (not (forall ((elisa_qN Int)) ...)) ...)), possibly abbreviated.
        if (len(node) >= 2 and isinstance(node[0], list) and node[0][:2] == ["_", "quant-inst"]
                and len(node[0]) == 3):
            lemma = expand(node[1], table)
            term_node = expand(node[0][2], table)
            match = re.search(rf"\(\({BINDER_PREFIX}([0-9]+) Int\)\)", render(lemma)) if lemma is not None else None
            term = from_smt(term_node, names) if term_node is not None else None
            if match and term is not None and depth(parse(term)) <= MAX_TERM_DEPTH:
                pair = (int(match.group(1)), term)
                if pair not in found:
                    found.append(pair)
        for item in node:
            walk(item)

    walk(proof)
    return found[:MAX_INSTANCES]


def render(node):
    return node if isinstance(node, str) else "(" + " ".join(render(item) for item in node) + ")"


def solve(problem):
    text, names = query(problem)
    try:
        result = subprocess.run([Z3, "-in"], input=text, capture_output=True, text=True,
                                timeout=TIMEOUT_MS / 1000 + 5)
    except (OSError, subprocess.TimeoutExpired):
        return []
    output = result.stdout.strip()
    if not output.startswith("unsat"):
        return []
    try:
        proof = parse("(" + output[len("unsat"):] + ")")
    except Malformed:
        return []
    return instances(proof, names)


def record(goal_id, found):
    text = f"2 {goal_id} {len(found)} " + " ".join(f'{index} "{term}"' for index, term in found)
    return text if len(text.encode()) <= MAX_RECORD_BYTES else None


def report_problems(path):
    run = subprocess.run([str(BINARY), "--json", str(path)], capture_output=True, text=True)
    try:
        report = json.loads(run.stdout)
    except json.JSONDecodeError:
        return {}
    found, stack = {}, [report]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            near = node.get("near_miss")
            if isinstance(near, dict) and isinstance(near.get("quantifier_problem"), dict) and "goal_id" in node:
                found[node["goal_id"]] = near["quantifier_problem"]
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    return found


def main(argv):
    hints_out = None
    if argv[:1] == ["--hints-out"] and len(argv) >= 2:
        hints_out, argv = argv[1], argv[2:]
    if argv[:1] == ["--problems"] and len(argv) == 2:
        problems = {int(k): v for k, v in json.loads(Path(argv[1]).read_text()).items()}
    elif len(argv) == 1:
        problems = report_problems(argv[0])
    else:
        print(__doc__.strip().splitlines()[-1], file=sys.stderr)
        return 2
    lines = []
    for goal_id in sorted(problems):
        try:
            found = solve(problems[goal_id])
        except (Malformed, KeyError, TypeError) as error:
            print(f"goal {goal_id}: problem refused: {error}", file=sys.stderr)
            continue
        line = record(goal_id, found) if found else None
        if line:
            lines.append(line)
    text = "".join(line + "\n" for line in lines)
    if hints_out:
        Path(hints_out).write_text(text)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
