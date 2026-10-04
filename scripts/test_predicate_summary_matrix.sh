#!/usr/bin/env bash
# Focused source/replay regressions for quantified predicate summary search.
# Run after the strict build. Every child retains its own original watchdog;
# this matrix does not raise budgets or substitute for the full standard suite.
set -euo pipefail
SUMMARY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
for SUMMARY_CASE in \
    boolean_predicate_equation \
    opaque_boolean_binding \
    quantifier_verified_call \
    finite_predicate_context \
    quantifier_predicate_summary \
    counted_length_scalar_prefix \
    counted_prefix_boolean_branch \
    extern_recovery_boundary_gap \
    counted_predicate_prefix; do
    python3 "$SUMMARY_ROOT/scripts/test_${SUMMARY_CASE}.py"
done
printf 'predicate summary matrix: nine positive/negative source-replay regressions passed\n'
