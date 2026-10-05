# Exact declaration/property inventory for the small kernel-core dogfood scope. This
# belongs beside, but separately from, the broad index/loop test matrix in 03.
dogfood_inventory_test_report="$ELISA_TEST_TMP/dogfood-kernel-core-inventory.json"
kernel_core_inventory_test_report="$ELISA_TEST_TMP/kernel-core-inventory.json"
run_json_report "$ROOT_DIR/examples/dogfood_kernel_core.elisa" >"$dogfood_inventory_test_report"
dogfood_core_contract_probe_status=$?
run_json_report "$ROOT_DIR/src/proof/kernel_core.elisa" >"$kernel_core_inventory_test_report"
kernel_core_self_probe_status=$?
if [[ "$dogfood_core_contract_probe_status" -ne 0 || "$kernel_core_self_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: kernel-core dogfood report generation\n' >&2
    exit 1
fi
python3 "$ROOT_DIR/scripts/check_dogfood_kernel_core_inventory.py" \
    --root "$ROOT_DIR" --report "$dogfood_inventory_test_report" \
    --inventory "$ROOT_DIR/scripts/dogfood_kernel_core_inventory.json" --slice kernel_core_fixture
python3 "$ROOT_DIR/scripts/check_dogfood_kernel_core_inventory.py" \
    --root "$ROOT_DIR" --report "$kernel_core_inventory_test_report" \
    --inventory "$ROOT_DIR/scripts/dogfood_kernel_core_inventory.json" --slice kernel_core
python3 "$ROOT_DIR/scripts/tests/test_dogfood_kernel_core_inventory.py"
