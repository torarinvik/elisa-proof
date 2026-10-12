"""Keep dogfood package export/replay on one generation-pinned product pair."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/dogfood.d/01-setup-and-includes.sh"
BUILD = ROOT / "scripts/build.sh"
source = SCRIPT.read_text(encoding="utf-8")
build_source = BUILD.read_text(encoding="utf-8")
setup = source.split("DOGFOOD_PAIR_JSON_PATH=", 1)[1].split("# build.sh has just refreshed", 1)[0]
portable = source.split("PORTABLE_PROOF_BIN=", 1)[1].split("for label in kernel_core", 1)[0]

assert 'ELISA_PROOF_PAIR_OUTPUT="$DOGFOOD_PAIR_JSON_PATH"' in setup
assert 'ELISA_PROOF_GENERATION_ROOT="${ELISA_PROOF_GENERATION_ROOT:-$ROOT_DIR/build/elisa-proof-generations}"' in setup
assert 'DOGFOOD_PAIR_JSON="$(<"$DOGFOOD_PAIR_JSON_PATH")"' in setup
assert "ELISA_PROOF_BIN ELISA_PROOF_REPLAY_BIN" in setup
assert '"$ELISA_PROOF_BIN"' in setup and '"$ELISA_PROOF_REPLAY_BIN"' in setup
assert 'ELISA_PROOF_PAIR_OUTPUT requires ELISA_PROOF_PRODUCTS=all' in build_source
assert build_source.index('ELISA_PROOF_PAIR_OUTPUT requires') < build_source.index('mkdir "$BUILD_LOCK"')
assert '"${ELISA_PROOF_GENERATION_ROOT:-$ROOT_DIR/build/elisa-proof-generations}"' in build_source
assert 'verify_product_pair.py" resolve' in build_source
assert '--generation-root "$PAIR_GENERATION_ROOT" >"$PAIR_OUTPUT_TEMP"' in build_source
assert build_source.index('trap cleanup_build EXIT') < build_source.index('verify_product_pair.py" resolve')
assert portable.startswith('"$ELISA_PROOF_BIN"\nPORTABLE_REPLAY_BIN="$ELISA_PROOF_REPLAY_BIN"\n')
assert '"$PORTABLE_PROOF_BIN" --package' in source
assert '"$PORTABLE_REPLAY_BIN" "$REPORT_DIR/$label.package.json"' in source
assert '"$ROOT_DIR/build/elisa-proof"' not in source
assert '"$ROOT_DIR/build/elisa-proof-replay"' not in source

print("dogfood portable package: one generation-pinned proof/replay resolution")
