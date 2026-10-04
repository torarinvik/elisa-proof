"""The matrix harness must preserve expected failures and count unexpected ones."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

if not __debug__:
    raise SystemExit("matrix harness checks must run without Python -O")

ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash")
assert BASH, "bash is required by the proof matrix"

with tempfile.TemporaryDirectory(prefix="elisa-proof-harness-") as temporary:
    root = Path(temporary)
    scripts = root / "scripts"
    parts = scripts / "test.d"
    parts.mkdir(parents=True)
    shutil.copyfile(ROOT / "scripts/test.sh", scripts / "test.sh")
    # Linking is irrelevant here: exercise the real control-flow harness with tiny steps.
    (scripts / "link_flags.sh").write_text("# no compile probes in this harness test\n")

    def run(steps, keep_going):
        (parts / "01-probes.sh").write_text(steps)
        environment = os.environ.copy()
        environment["KEEP_GOING"] = str(keep_going)
        result = subprocess.run([BASH, str(scripts / "test.sh")], env=environment,
                                capture_output=True, text=True, timeout=20)
        return result

    expected = """set +e
false | true
statuses=("${PIPESTATUS[@]}")
[[ "${statuses[*]}" == '1 0' ]] || exit 9
true | false
statuses=("${PIPESTATUS[@]}")
[[ "${statuses[*]}" == '0 1' ]] || exit 9
set -e
printf 'expected failures retained\\n'
"""
    for mode in (0, 1):
        result = run(expected, mode)
        assert result.returncode == 0, (mode, result.stdout, result.stderr)
        assert result.stdout == "expected failures retained\n", result.stdout
        assert "step failed" not in result.stderr and "command failed" not in result.stderr

    # One unhandled command, one explicit nonzero exit, and one unhandled pipeline.
    # Expected failures above must not contribute to the final count.
    failures = expected + """false
printf 'after command\\n'
exit 7
printf 'after exit\\n'
true | false
printf 'after pipeline\\n'
if [[ "$KEEP_GOING" == 1 ]]; then
    printf 'failure count: %s\\n' "$keep_going_failures"
    [[ "$keep_going_failures" == 3 ]] || exit 9
    builtin exit 1
fi
"""
    result = run(failures, 0)
    assert result.returncode == 1, (result.returncode, result.stderr)
    assert result.stdout == "expected failures retained\n", result.stdout
    result = run(failures, 1)
    assert result.returncode == 1, (result.returncode, result.stderr)
    assert result.stdout == ("expected failures retained\nafter command\nafter exit\n"
                             "after pipeline\nfailure count: 3\n"), result.stdout
    assert result.stderr.count("command failed") == 2, result.stderr
    assert result.stderr.count("step failed (status 7)") == 1, result.stderr

print("matrix harness: expected pipeline statuses retained; fail-fast and keep-going counts agree")
