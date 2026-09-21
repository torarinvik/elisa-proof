"""Validate the standalone replay audit's coverage and trust boundary."""

import json
import sys


REQUIRED_VERIFIED_DECLARATIONS = {
    "proof_kernel_replay_difference_affine_query",
    "proof_kernel_replay_ident_name",
    "proof_kernel_replay_node_at",
    "proof_kernel_replay_bool_at",
    "proof_kernel_replay_bool_set",
    "proof_kernel_replay_child_at",
    "proof_kernel_replay_child_range_valid",
    "proof_kernel_replay_constant_leaf",
    "proof_kernel_replay_constant_comparison",
    "proof_kernel_replay_direct_literal_comparison",
    "proof_kernel_replay_order_atom",
    "proof_kernel_replay_peer_is_nameable",
    "proof_kernel_replay_zero_literal",
    "proof_kernel_replay_product_operands",
    "proof_kernel_replay_binary_operands",
    "proof_kernel_replay_negated_operand",
    "proof_kernel_replay_integer_literal",
    "proof_kernel_replay_name_pin",
    "proof_kernel_replay_pinned_constant",
    "proof_kernel_replay_false_boolean_literal",
    "proof_kernel_replay_negated_true_boolean_literal",
    "proof_kernel_replay_conjunction_operands",
    "proof_kernel_replay_facts_inconsistent_remaining",
    "proof_kernel_replay_facts_inconsistent",
    "proof_kernel_replay_expr_leaf_equal",
    "proof_kernel_replay_expr_call_argument_enqueue",
    "proof_kernel_replay_expr_child_enqueue",
    "proof_kernel_replay_expr_pair_enqueue",
    "proof_kernel_replay_expr_pair_nodes_valid",
    "proof_kernel_replay_constant_int",
    "proof_kernel_replay_constant_int_remaining",
    "proof_kernel_replay_scalar_kind",
    "proof_kernel_replay_arena_shape_valid",
    "proof_kernel_replay_arena_child_kind_valid",
    "proof_kernel_replay_model_value_at",
    "proof_kernel_replay_difference_query",
    "proof_kernel_replay_required_identity_present",
}
MIN_REPLAYED_CERTIFICATES = 270


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    report = json.load(sys.stdin)
    summary = report["summary"]
    replay = report["replay"]

    require(report["status"] == "failed", "standalone audit must remain a failed corpus")
    require(report["verification_state"] != "proved", "standalone audit unexpectedly became proved")
    require(summary["semantic_errors"] == 0, "standalone audit introduced semantic errors")
    require(
        summary["proven"] >= MIN_REPLAYED_CERTIFICATES,
        f"standalone proof coverage fell below {MIN_REPLAYED_CERTIFICATES}: {summary['proven']}",
    )
    require(
        replay["certificates"] == replay["replayed"],
        f"certificate replay count mismatch: {replay}",
    )
    require(replay["gaps"] == 0, f"standalone audit has replay gaps: {replay}")

    verified = {
        declaration["name"]
        for declaration in report["declaration_details"]
        if declaration["kind"] == "function" and declaration["verified"]
    }
    missing = sorted(REQUIRED_VERIFIED_DECLARATIONS - verified)
    require(not missing, f"required verified declarations became unverified: {missing}")

    budget_kinds = {"control-flow-analysis-budget", "resource-analysis-budget"}
    bad_budget_findings = [
        finding
        for finding in report["findings"]
        if finding["kind"] in budget_kinds and finding["status"] != "unsupported"
    ]
    require(not bad_budget_findings, f"budget exhaustion was misclassified: {bad_budget_findings}")
    for finding in report["findings"]:
        if finding["kind"] in budget_kinds | {"frame-analysis-budget"}:
            budget = finding.get("budget")
            require(isinstance(budget, dict), f"budget finding lacks measured state: {finding}")
            require(
                isinstance(budget.get("observed"), int)
                and isinstance(budget.get("limit"), int)
                and budget["observed"] > budget["limit"],
                f"budget finding has inconsistent measurements: {finding}",
            )
    evaluator_budget_findings = [
        finding
        for finding in report["findings"]
        if finding["name"] == "proof_kernel_replay_constant_int"
        and finding["kind"] in budget_kinds
    ]
    require(
        all(finding["line"] > 0 for finding in evaluator_budget_findings),
        f"constant evaluator budget finding lost its source location: {evaluator_budget_findings}",
    )
    unsigned_findings = [
        finding
        for finding in report["findings"]
        if finding["kind"] == "contract-expression-unsupported"
        and "unsigned local" in finding["message"]
    ]
    require(not unsigned_findings, f"unsigned-local containment regressed: {unsigned_findings}")
    require(report["trust"]["trusted_assumptions"] == [], "standalone audit gained trusted assumptions")


if __name__ == "__main__":
    main()
