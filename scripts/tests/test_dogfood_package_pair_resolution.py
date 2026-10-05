"""Keep dogfood package export/replay on one generation-pinned product pair."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/dogfood.d/01-setup-and-includes.sh"
source = SCRIPT.read_text(encoding="utf-8")
section = source.split("portable_pair_json=", 1)[1].split("python3 -", 1)[0]

assert section.count("verify_product_pair.py\" resolve") == 1, section
assert "--generation-root \"${ELISA_PROOF_GENERATION_ROOT:-$ROOT_DIR/build/elisa-proof-generations}\"" in section
assert 'PORTABLE_PROOF_BIN="${portable_pair_paths%%$' in source
assert 'PORTABLE_REPLAY_BIN="${portable_pair_paths#*$' in source
assert '"$PORTABLE_PROOF_BIN" --package' in source
assert '"$PORTABLE_REPLAY_BIN" "$REPORT_DIR/$label.package.json"' in source
assert '"$ROOT_DIR/build/elisa-proof" --package' not in section
assert '"$ROOT_DIR/build/elisa-proof-replay"' not in section

print("dogfood portable package: one generation-pinned proof/replay resolution")
