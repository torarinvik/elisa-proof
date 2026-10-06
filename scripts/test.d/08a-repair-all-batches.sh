# Sourced by scripts/test.sh after 08-lends-and-calls.sh: whole-file `--repair-all` batches.
# Uses $proof_render_dir from part 08.

# `--repair-all` walks the unresolved goals of a whole file in one pass. It repairs nothing the
# checker already proved, reports each open goal separately, and its verdict is the conjunction of
# the per-goal ones — a file with any unrepaired goal is `partial` and exits non-zero.
set +e
"$ROOT_DIR/build/elisa-proof" --repair-all "$ROOT_DIR/examples/verified.elisa" > "$proof_render_dir/batch_clean.json"
proof_batch_clean_status=$?
