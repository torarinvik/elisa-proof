#!/usr/bin/env python3
"""Focused contracts for the bounded P-01 baseline runner."""

import importlib.util
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

SCRIPT = Path(__file__).with_name("p01_baseline.py")
SPEC = importlib.util.spec_from_file_location("p01_baseline", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="p01-test-") as temporary:
        root = Path(temporary)
        binary = root / "proof"
        report = {"status": "proved", "verification_state": "proved",
                  "summary": {"obligations": 1, "proven": 1, "unproven": 0,
                              "semantic_errors": 0},
                  "declaration_details": [{"verified": True}], "goals": [{}],
                  "measurements": {"goal_cache_hits": 1, "goal_cache_misses": 2,
                                   "control_flow_steps": 3, "live_facts_peak": 4},
                  "replay": {"certificates": 1, "replayed": 1, "gaps": 0}}
        binary.write_text("#!/usr/bin/env python3\nimport json\nprint(" +
                          repr(json.dumps(report)) + ")\n", encoding="utf-8")
        binary.chmod(0o755)
        fixture = root / "fixture.elisa"
        fixture.write_text("def proof():\n    ensure true\n", encoding="utf-8")
        old = MODULE.FIXTURES
        MODULE.FIXTURES = (("test", fixture),)
        try:
            result = MODULE.run(SimpleNamespace(binary=binary, timeout=5, rss_limit_kib=500000))
        finally:
            MODULE.FIXTURES = old
        assert result["schema"] == "elisa-proof-p01-baseline-v1"
        assert result["binary"]["sha256"] == MODULE.identity(binary)["sha256"]
        case = result["cases"][0]
        assert set(case["scenarios"]) == {"cold", "warm", "no_op"}
        assert case["source"]["sha256"] != case["comment_edit_source"]["sha256"]
        measurements = [item for scenario in case["scenarios"].values()
                        for item in scenario["measurements"]]
        assert all(item["replay_gaps"] == 0 for item in measurements)
        MODULE.check_report(measurements[0], MODULE.EXPECTED_OUTCOMES["real_small"])
        assert measurements[0]["goal_cache_hits"] == 1
        assert measurements[0]["goal_cache_misses"] == 2
        assert measurements[0]["control_flow_steps"] == 3
        assert measurements[0]["live_facts_peak"] == 4
        negative_expected = MODULE.EXPECTED_OUTCOMES["adversarial"]
        try:
            MODULE.check_report(measurements[0], negative_expected)
        except RuntimeError as error:
            assert "negative fixture was accepted" in str(error)
        else:
            raise AssertionError("negative fixture acceptance was not detected")
        malformed = {"report_complete": False, "stop_reason": None}
        try:
            MODULE.check_report(malformed)
        except RuntimeError as error:
            assert "complete JSON" in str(error)
        else:
            raise AssertionError("incomplete report was accepted")
        print("P-01 baseline: fixed identities, scenario labels and replay completeness enforced")


if __name__ == "__main__":
    main()
