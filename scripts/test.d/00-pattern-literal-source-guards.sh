# shellcheck shell=bash
# Source-only guard regression; runtime collisions run in 01-setup-and-python-suites.sh.
python3 "$ROOT_DIR/scripts/test_pattern_literal_source_guards.py"
python3 "$ROOT_DIR/scripts/test_elisascript_report_output_port_parity.py"
python3 "$ROOT_DIR/scripts/test_elisascript_report_output_reader_contract.py"
python3 "$ROOT_DIR/scripts/test_scheduler_incremental_source_guards.py"
python3 "$ROOT_DIR/scripts/test_source_authority_static_guards.py"
python3 "$ROOT_DIR/scripts/test_checked_view_row_authority_static.py"
python3 "$ROOT_DIR/scripts/test_loop_invariant_source_guard.py"
python3 "$ROOT_DIR/scripts/test_resource_binding_identity_source_guard.py"
python3 "$ROOT_DIR/scripts/test_source_lemma_multiplicity_static.py"
python3 "$ROOT_DIR/scripts/test_resource_call_storage_confinement_static.py"
python3 "$ROOT_DIR/scripts/test_structural_replay_source_guards.py"
