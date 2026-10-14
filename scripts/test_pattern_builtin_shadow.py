"""A source alias named like a builtin must not authorize typed pattern facts."""

import json
from pathlib import Path
import subprocess
import tempfile

from qualified_test_binary import proof_test_binary


ROOT = Path(__file__).resolve().parents[1]
BINARY = proof_test_binary(ROOT)
SOURCE = '''
type sview = u64

def shadowed_string_pattern(value: sview) -> i64:
    ensure result == 0
    match value:
        "ready":
            return 1
        _:
            return 0
'''
SIBLING_SHADOW_SOURCE = '''
module Imported:
    public:
        type char = u64

module Owner:
    public:
        def builtin_char_pattern(value: char) -> i64:
            ensure result >= 0
            match value:
                'A':
                    assert value == 'A' by:
                        assert value == 'A'
                    return 1
                _:
                    return 0

module Sibling:
    from Imported import char
'''
OWNER_IMPORT_SHADOW_SOURCE = '''
module Imported:
    public:
        type char = u64

module Owner:
    from Imported import char
    public:
        def imported_char_pattern(value: char) -> i64:
            ensure result > 0
            match value:
                'A':
                    return 1
                _:
                    return 0
'''


def run_report(*arguments):
    result = subprocess.run([BINARY, *arguments], cwd=ROOT, capture_output=True,
                            text=True, timeout=120)
    report = json.loads(result.stdout)
    assert result.returncode == 1 and report["status"] == "failed", report
    assert report["source"]["admissible"] is True, report["source"]
    assert report["summary"]["semantic_errors"] == 0, report["semantic_diagnostics"]
    assert report["replay"]["gaps"] == 0, report["replay"]
    assert report["replay"]["certificates"] == report["replay"]["replayed"], report["replay"]
    assert not report["trust"]["trusted_assumptions"], report["trust"]
    assert any(row["name"] == "shadowed_string_pattern" and not row["proved"]
               for row in report["functions"]), report["functions"]
    assert any(row["name"] == "shadowed_string_pattern" and not row["proven"]
               for row in report["goals"]), report["goals"]
    assert any(row["name"] == "shadowed_string_pattern" and row["kind"] == "ensure-unproven"
               for row in report["findings"]), report["findings"]
    return report


with tempfile.TemporaryDirectory() as directory:
    source = Path(directory) / "builtin-shadow.elisa"
    source.write_text(SOURCE, encoding="utf-8")
    run_report("--json", str(source))
    focused = run_report("--function-json", "shadowed_string_pattern", str(source))
    assert focused["source"]["admissible"] is True

    # A same-spelled type in a sibling module must not hide the builtin char type
    # used by this function in Owner.
    sibling_source = Path(directory) / "sibling-builtin-shadow.elisa"
    sibling_source.write_text(SIBLING_SHADOW_SOURCE, encoding="utf-8")
    sibling_result = subprocess.run([BINARY, "--json", str(sibling_source)], cwd=ROOT,
                                    capture_output=True, text=True, timeout=120)
    sibling_report = json.loads(sibling_result.stdout)
    assert sibling_result.returncode == 0 and sibling_report["status"] == "proved", sibling_report
    assert sibling_report["source"]["admissible"] is True, sibling_report["source"]
    assert sibling_report["replay"]["gaps"] == 0, sibling_report["replay"]
    assert sibling_report["functions_complete"] is True, sibling_report
    assert any(row["name"] == "Owner" and row["proved"]
               for row in sibling_report["functions"]), sibling_report["functions"]

    # The same imported alias must block builtin evidence when the import is in the owner.
    owner_import_source = Path(directory) / "owner-import-builtin-shadow.elisa"
    owner_import_source.write_text(OWNER_IMPORT_SHADOW_SOURCE, encoding="utf-8")
    owner_import_result = subprocess.run([BINARY, "--json", str(owner_import_source)], cwd=ROOT,
                                         capture_output=True, text=True, timeout=120)
    owner_import_report = json.loads(owner_import_result.stdout)
    assert owner_import_result.returncode == 1 and owner_import_report["status"] == "failed", owner_import_report
    assert owner_import_report["source"]["admissible"] is True, owner_import_report["source"]
    assert owner_import_report["summary"]["semantic_errors"] == 0, owner_import_report["semantic_diagnostics"]
    assert owner_import_report["replay"]["gaps"] == 0, owner_import_report["replay"]
    assert any(row["name"] == "imported_char_pattern" and row["kind"] == "ensure-unproven"
               for row in owner_import_report["findings"]), owner_import_report["findings"]

print("pattern builtin shadow: reject root aliases and preserve exact sibling-module builtin identity")
