# R-004 report/declaration inventory completeness and non-proved partial outcomes.
ELISA_PROOF_BIN="$ROOT_DIR/build/elisa-proof" \
ELISA_REPORT_INVENTORY_HARNESS="$standalone_probe_dir/report-invariants" \
    python3 "$ROOT_DIR/scripts/tests/test_report_inventory_completeness.py"
