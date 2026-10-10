"""Temporary visibility copies retain their original include resolution."""
from pathlib import Path
import re
import tempfile
from source_binding_harness_support import _test_replay_includes

ROOT = Path(__file__).resolve().parents[1]
original = ROOT / "src/proof/replay/source_binding_validation/immutable_bindings.elisa"
helper_paths = [original,
    ROOT / "src/proof/replay/source_binding_validation.elisa",
    ROOT / "src/proof/replay/source_binding_validation/typed_return_constants.elisa"]
before = {path: path.read_bytes() for path in helper_paths}
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
    typed_original = helper_paths[2].read_text()
    typed_generated = (scratch / "typed_return_constants_test.elisa").read_text()
    private_count = len(re.findall(r"^    private:$", typed_original, re.MULTILINE))
    assert private_count >= 2
    assert len(re.findall(r"^    public:$", typed_generated, re.MULTILINE)) == private_count
    assert not re.search(r"^    private:$", typed_generated, re.MULTILINE)
for path in helper_paths:
    assert path.read_bytes() == before[path]
print("source-binding harness: relocated includes resolve; production visibility unchanged")
