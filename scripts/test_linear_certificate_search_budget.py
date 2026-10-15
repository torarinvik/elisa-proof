"""Linear-certificate elimination meters every input and combination loop."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "src/proof/linear/linear_certificate_search.elisa").read_text(encoding="utf-8")
widths = (ROOT / "src/proof/linear/normalized_differences.elisa").read_text(encoding="utf-8")

local_start = widths.split("def proof_linear_search_width_local_start(", 1)[1].split(
    "# Search variants meter", 1
)[0]
assert "remaining: usize = work_limit - work" in local_start
assert "PROOF_LINEAR_SAFETY_WORK_LIMIT - allowance" in local_start
for width_scan in (
    "proof_signed_width_in_expression_with_work(expression, markers, 0, &local_work, &exhausted)",
    "proof_unsigned_width_in_expression_with_work(expression, markers, &local_work, &exhausted)",
    "proof_signed_width_in_expression_with_work(left, markers, 0, &local_work, &exhausted)",
    "proof_signed_width_in_expression_with_work(right, markers, 0, &local_work, &exhausted)",
):
    assert width_scan in widths
assert "work <- work_limit" in widths
assert "local_work - start.baseline" in widths

gcd = source.split("def proof_linear_gcd_with_work(", 1)[1].split(
    "# Read `fact`", 1
)[0]
assert "while second != 0 |first, second, work, work_limit, metered|" in gcd
assert "proof_linear_search_take_work(work, work_limit, 1)" in gcd

combine = source.split("def proof_linear_combine(", 1)[1].split(
    "def proof_linear_copy_row(", 1
)[0]
for loop in (
    "for position in 0..<(atoms + 1 + slots)",
    "for position in 0..<entries.count",
):
    assert combine.count(loop) >= 1
assert combine.count("proof_linear_search_take_work(work, work_limit, 1)") >= 2
gcd_pass = combine.split("for position in 0..<entries.count", 1)[1].split(
    "divisor <- 1 if divisor == 0", 1
)[0]
assert "proof_linear_search_take_work(work, work_limit, 1)" in gcd_pass.split(
    "entry: i64 = entries[position]", 1
)[0]
assert "proof_linear_gcd_with_work(divisor, entry, work, work_limit, metered)" in combine
assert "return false if not gcd.complete" in combine

eliminate = source.split("def proof_linear_eliminate(", 1)[1].split(
    "# The names a fact", 1
)[0]
assert "proof_linear_combine(rows, upper, 0 - lower_value, lower, upper_value, atoms, slots, output, work, work_limit, metered)" in eliminate
assert "proof_linear_copy_row(rows, row, atoms, slots, output)" in eliminate
assert "proof_linear_search_take_work(work, work_limit, atoms + slots + 1)" in eliminate

search = source.split("def proof_linear_certificate_search(", 1)[1]
assert "proof_linear_search_width_local_start(work, work_limit)" in search
assert "marker_work: mutable usize = marker_start.baseline" in search
assert "marker_work - marker_start.baseline" in search

print("linear certificate search budget: recursive width/index walks and row loops enforce shared work")
