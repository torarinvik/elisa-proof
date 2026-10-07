"""Temporary visibility copies retain their original include resolution."""
from pathlib import Path
import re
import tempfile
from source_binding_harness_support import _test_replay_includes

ROOT = Path(__file__).resolve().parents[1]
original = ROOT / "src/proof/replay/source_binding_validation/immutable_bindings.elisa"
before = original.read_bytes()
with tempfile.TemporaryDirectory() as directory:
    scratch = Path(directory)
    expanded = _test_replay_includes(ROOT, scratch)
    generated = scratch / "immutable_bindings_test.elisa"
    source = generated.read_text()
    assert '    public:' in source
    assert str(generated) in expanded
    includes = re.findall(r'^include "([^"\n]+)"$', source, re.MULTILINE)
    assert includes
    for include in includes:
        target = Path(include)
        assert target.is_absolute() and target.is_file(), include
    expected = original.parent / "value_block_immutable_bindings.elisa"
    assert str(expected.resolve()) in includes
assert original.read_bytes() == before
print("source-binding harness: relocated includes resolve; production visibility unchanged")
