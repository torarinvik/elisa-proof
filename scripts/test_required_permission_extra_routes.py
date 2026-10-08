"""Missing permissions cannot be hidden by focused, compact, hinted or correspondence output."""
import ast
import json
from pathlib import Path
import tempfile
import test_source_admission_matrix as admission

ROOT = Path(__file__).resolve().parents[1]
tree = ast.parse((ROOT / "scripts/test_required_permission_cli_admission.py").read_text())
negative = next(ast.literal_eval(node.value) for node in tree.body
                if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Attribute) and target.attr == "MALFORMED"
                        for target in node.targets))
positive = next(ast.literal_eval(node.value) for node in tree.body
                if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == "positive"
                        for target in node.targets))

with tempfile.TemporaryDirectory() as temporary:
    directory = Path(temporary)
    hints = directory / "hints.txt"
    hints.write_text("# empty hint stream\n")

    def extra_routes(source):
        return (
            ("summary", ["--summary-json", source]),
            ("function", ["--function-json", "successor", source]),
            ("explain", ["--explain", admission.GOAL, source]),
            ("hints", ["--linear-hints", hints, source]),
        )

    for index, fragment in enumerate((b"",) + positive):
        source = directory / ("granted-" + str(index) + ".elisa")
        source.write_bytes(admission.BASE + b"\n" + fragment)
        for name, arguments in extra_routes(source):
            result = admission.run(*arguments)
            assert result.returncode == 0, (index, name, result.stdout[:500])

    supported = ROOT / "examples/branch_negation.elisa"
    rendered = admission.run("--package", supported)
    assert rendered.returncode == 0, rendered.stdout[:500]
    package = directory / "supported.package.json"
    package.write_bytes(rendered.stdout)
    checked = admission.run("--correspondence", package, supported)
    assert checked.returncode == 0, checked.stdout[:500]
    assert json.loads(checked.stdout)["source_admissible"] is True

    for variant, fragment in negative.items():
        source = directory / (variant + ".elisa")
        source.write_bytes(admission.BASE + fragment)
        for name, arguments in extra_routes(source):
            result = admission.run(*arguments)
            assert result.returncode != 0, (variant, name, result.stdout[:500])
            if name != "explain":
                report = json.loads(result.stdout)
                assert report["status"] != "proved", (variant, name, report)
        result = admission.run("--correspondence", package, source)
        assert result.returncode != 0, (variant, "correspondence", result.stdout[:500])
        assert json.loads(result.stdout)["source_admissible"] is False

print("Permission admission: five additional modes refuse all five violations; four granted controls and supported correspondence remain admitted")

