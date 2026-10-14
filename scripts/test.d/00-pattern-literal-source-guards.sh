# shellcheck shell=bash
# Source-only guard regression; runtime collisions run in 01-setup-and-python-suites.sh.
python3 "$ROOT_DIR/scripts/test_pattern_literal_source_guards.py"
python3 "$ROOT_DIR/scripts/test_scheduler_incremental_source_guards.py"
python3 "$ROOT_DIR/scripts/test_source_authority_static_guards.py"
python3 "$ROOT_DIR/scripts/test_structural_replay_source_guards.py"
