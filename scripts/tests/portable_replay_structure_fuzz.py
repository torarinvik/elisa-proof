"""Deterministic structure-aware parser/replay fuzzing for portable packages.

Loaded by ``test_portable_replay.py`` after its positive package setup. Every probe runs
the replay executable in a fresh process; unexpected outcomes are retained as minimized
JSON seeds under ``scripts/tests/r006_fuzz_seeds``.
"""
import hashlib
import json
import copy
from pathlib import Path
import resource
import subprocess
import time

from portable_replay_support import *

SEEDS = ROOT / "scripts/tests/r006_fuzz_seeds"
WALL_LIMIT_SECONDS = 5
MAX_CAPTURE_BYTES = 4 * 1024 * 1024
RSS_LIMIT_BYTES = 512 * 1024 * 1024
CPU_LIMIT_SECONDS = 4
MINIMIZATION_ATTEMPT_LIMIT = 64
PEAK_RSS_BYTES = 0
PEAK_CPU_SECONDS = 0.0
PEAK_WALL_SECONDS = 0.0


def compact_seed(data):
    """Whitespace minimization is semantics-preserving and keeps the exact failing tree."""
    return json.dumps(data, ensure_ascii=True, separators=(",", ":")).encode("ascii")


def run_fresh(data, label, must_refuse=True):
    global LAST_CHILD_CPU, PEAK_RSS_BYTES, PEAK_CPU_SECONDS, PEAK_WALL_SECONDS
    raw = data if isinstance(data, bytes) else compact_seed(data)
    digest = hashlib.sha256(raw).hexdigest()[:16]
    path = WORK / ("r006-%s-%s.json" % (label, digest))
    path.write_bytes(raw)
    started = time.monotonic()
    child = subprocess.Popen([str(REPLAY), str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             preexec_fn=install_cpu_limit)
    peak_rss = 0
    try:
        while child.poll() is None:
            elapsed = time.monotonic() - started
            if elapsed >= WALL_LIMIT_SECONDS:
                child.kill()
                child.communicate()
                retain(raw, label + "-timeout")
                raise AssertionError("fresh replay timed out after %ds: %s" %
                                     (WALL_LIMIT_SECONDS, label))
            sample = subprocess.run(["/bin/ps", "-o", "rss=", "-p", str(child.pid)],
                                    capture_output=True, text=True, check=False)
            try:
                peak_rss = max(peak_rss, int(sample.stdout.strip()) * 1024)
            except ValueError:
                pass
            if peak_rss > RSS_LIMIT_BYTES:
                child.kill()
                child.communicate()
                retain(raw, label + "-rss-limit")
                raise AssertionError("fresh replay exceeded %d-byte RSS limit: %s" %
                                     (RSS_LIMIT_BYTES, label))
            time.sleep(0.01)
        stdout, stderr = child.communicate()
    except subprocess.TimeoutExpired as error:
        retain(raw, label + "-timeout")
        raise AssertionError("fresh replay timed out after %ds: %s" % (WALL_LIMIT_SECONDS, label)) from error
    elapsed = time.monotonic() - started
    if len(stdout) > MAX_CAPTURE_BYTES or len(stderr) > MAX_CAPTURE_BYTES:
        retain(raw, label + "-output-flood")
        raise AssertionError("replay exceeded bounded output capture: " + label)
    try:
        result = json.loads(stdout)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        retain(raw, label + "-invalid-output")
        raise AssertionError("replay emitted no structured result: %s (%d, %r)" %
                             (label, child.returncode, stdout[:300])) from error
    valid = (child.returncode in (0, 1) and
             result.get("format") == "elisa-proof-replay-result-v1" and
             result.get("trust") == TRUST)
    summary = result.get("summary", {})
    valid = valid and summary.get("theorems", 0) == summary.get("replayed", 0) + summary.get("not_replayed", 0)
    valid = valid and (result.get("status") != "replayed" or
                       (summary.get("theorems", 0) > 0 and summary.get("not_replayed") == 0))
    if must_refuse:
        valid = valid and child.returncode == 1 and result.get("status") != "replayed"
        theorem_results = result.get("theorems", [])
        valid = valid and all(theorem.get("status") != "replayed" for theorem in theorem_results)
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    # CPU times are cumulative for this test process; CPU_LIMIT is also enforced by
    # RLIMIT_CPU for each fresh replay child, while wall time is independently polled.
    global LAST_CHILD_CPU
    cpu_seconds = usage.ru_utime + usage.ru_stime - LAST_CHILD_CPU
    LAST_CHILD_CPU = usage.ru_utime + usage.ru_stime
    PEAK_CPU_SECONDS = max(PEAK_CPU_SECONDS, cpu_seconds)
    PEAK_RSS_BYTES = max(PEAK_RSS_BYTES, peak_rss)
    valid = valid and cpu_seconds <= CPU_LIMIT_SECONDS and peak_rss <= RSS_LIMIT_BYTES
    PEAK_WALL_SECONDS = max(PEAK_WALL_SECONDS, elapsed)
    if not valid:
        retain(raw, label + "-unexpected")
        raise AssertionError("invalid/partial replay outcome for %s in %.3fs: %s" %
                             (label, elapsed, result))
    return result, elapsed


def install_cpu_limit():
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_LIMIT_SECONDS, CPU_LIMIT_SECONDS))


LAST_CHILD_CPU = resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime + resource.getrusage(resource.RUSAGE_CHILDREN).ru_stime


# The nominal 4,096-hypothesis boundary collides with the independent 65,536-byte string cap.
# A bool leaf is the shortest proposition identity: `(bool::1:"":"")` is 15 bytes. The
# canonical statement for 4,096 copies is 65,572 bytes, so the statement field is rejected as
# theorem-schema before the theorem-level hypothesis budget can admit an exact positive. Keep
# this control bounded and pin the ordering rather than claiming the nominal limit is reachable.
boundary = copy.deepcopy(base)
short_proposition = append_node(boundary, "bool", value="1")
origin = copy.deepcopy(assumption["hypothesis_origins"][0])
exact_hypotheses = copy.deepcopy(assumption)
exact_hypotheses["conclusion"] = short_proposition
exact_hypotheses["hypotheses"] = [short_proposition] * 4096
exact_hypotheses["hypothesis_origins"] = [copy.deepcopy(origin)] * 4096
exact_hypotheses = reseal(boundary, exact_hypotheses)
assert len(exact_hypotheses["statement"].encode("utf-8")) == 65572
exact_result, _ = run_fresh(with_theorem(boundary, exact_hypotheses),
                            "hypothesis-budget-exact-shadow", must_refuse=True)
assert exact_result["status"] == "malformed" and exact_result["reason"] == "theorem-schema", exact_result
assert exact_result["summary"] == {"theorems": 1, "replayed": 0, "not_replayed": 1}, exact_result
assert all(theorem["status"] != "replayed" for theorem in exact_result["theorems"]), exact_result

# A compact existing statement lets the count check run first for 4,097. Its identity is
# intentionally stale because a canonical one-over statement would exceed STRING_BYTES too;
# this pins hypothesis-budget refusal ordering, not a valid portable theorem.
over_hypotheses = copy.deepcopy(exact_hypotheses)
over_hypotheses["hypotheses"].append(short_proposition)
over_hypotheses["hypothesis_origins"].append(copy.deepcopy(origin))
over_hypotheses["statement"] = assumption["statement"]
over_hypotheses["goal_fingerprint"] = assumption["goal_fingerprint"]
over_result, _ = run_fresh(with_theorem(boundary, over_hypotheses),
                           "hypothesis-budget-over-shadow", must_refuse=True)
assert over_result["status"] == "over-budget" and over_result["reason"] == "hypothesis-budget", over_result
assert over_result["summary"] == {"theorems": 1, "replayed": 0, "not_replayed": 1}, over_result
assert len(over_result["theorems"]) == 1 and over_result["theorems"][0]["status"] == "over-budget", over_result


def retain(raw, label):
    """Structurally delta-minimize and retain an unexpected package seed."""
    SEEDS.mkdir(parents=True, exist_ok=True)
    compact = raw if isinstance(raw, bytes) else compact_seed(raw)
    try:
        value = json.loads(compact)
    except (UnicodeDecodeError, json.JSONDecodeError):
        value = None
    if isinstance(value, (dict, list)):
        target = failure_signature(compact, label)
        attempts = [0]
        value = minimize_json(value, target, label, attempts)
        compact = compact_seed(value)
    name = "%s-%s.json" % (label, hashlib.sha256(compact).hexdigest()[:16])
    (SEEDS / name).write_bytes(compact)


def failure_signature(raw, label):
    path = WORK / ("r006-minimize-%s.json" % hashlib.sha256(raw).hexdigest()[:16])
    path.write_bytes(raw)
    child = subprocess.Popen([str(REPLAY), str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             preexec_fn=install_cpu_limit)
    started = time.monotonic()
    while child.poll() is None:
        if time.monotonic() - started >= WALL_LIMIT_SECONDS:
            child.kill()
            child.communicate()
            return "timeout"
        sample = subprocess.run(["/bin/ps", "-o", "rss=", "-p", str(child.pid)],
                                capture_output=True, text=True, check=False)
        try:
            if int(sample.stdout.strip()) * 1024 > RSS_LIMIT_BYTES:
                child.kill()
                child.communicate()
                return "rss-limit"
        except ValueError:
            pass
        time.sleep(0.01)
    stdout, _ = child.communicate()
    if child.returncode < 0:
        return "signal-" + str(-child.returncode)
    try:
        result = json.loads(stdout)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return "invalid-output"
    if result.get("format") != "elisa-proof-replay-result-v1" or result.get("trust") != TRUST:
        return "invalid-result"
    if result.get("status") == "replayed":
        return "accepted"
    return "refused-" + str(result.get("reason"))


def minimize_json(value, target, label, attempts):
    """Greedily remove object members/array entries while retaining the same failure class."""
    if attempts[0] >= MINIMIZATION_ATTEMPT_LIMIT:
        return value
    if isinstance(value, dict):
        for key in list(value):
            if attempts[0] >= MINIMIZATION_ATTEMPT_LIMIT:
                break
            candidate = dict(value)
            del candidate[key]
            attempts[0] += 1
            if failure_signature(compact_seed(candidate), label) == target:
                value = candidate
        for key in list(value):
            value[key] = minimize_json(value[key], target, label, attempts)
    elif isinstance(value, list):
        index = 0
        while index < len(value) and attempts[0] < MINIMIZATION_ATTEMPT_LIMIT:
            candidate = list(value)
            del candidate[index]
            attempts[0] += 1
            if failure_signature(compact_seed(candidate), label) == target:
                value = candidate
            else:
                value[index] = minimize_json(value[index], target, label, attempts)
                index += 1
    return value


def malformed_case(package, label, reason=None):
    result, _ = run_fresh(package, label, must_refuse=True)
    if reason is not None:
        assert result["reason"] == reason, (label, result)


# Keep a bounded positive control in this structure-aware runner as well as in the
# enclosing package test: the malformed mutations below must not disturb valid replay.
positive, _ = run_fresh(with_theorem(base, assumption), "structure-positive-control",
                        must_refuse=False)
assert positive["status"] == "replayed" and positive["summary"] == {
    "theorems": 1, "replayed": 1, "not_replayed": 0
}, positive

# Every node record has three required textual metadata fields, independent of node kind.
# Mutate each field's JSON type on the theorem's reachable conclusion node; reject at schema
# admission, before a theorem result can be partially reported. These field-type mutations
# are distinct from the existing numeric payload, index, and unknown-kind cases below.
for field, value in (("operator", []), ("name", None), ("secondary_name", 7)):
    malformed = with_theorem(base, assumption)
    malformed["kernel"]["nodes"][assumption["conclusion"]][field] = value
    result, _ = run_fresh(malformed, "node-text-schema-" + field, must_refuse=True)
    assert result["reason"] == "node-schema", (field, result)
    assert result["summary"] == {"theorems": 0, "replayed": 0, "not_replayed": 0}, (field, result)
    assert result["theorems"] == [], (field, result)


# Deeply nested wrong-typed payloads stress parser recursion while ensuring the strict
# package reader, not theorem comparison, must refuse each structure.
nest_template = compact_seed(base).decode("ascii")
needle = b'"admissible":true'
for depth in (32, 128, 512, 2048, 8192):
    nested = b"[" * depth + b"0" + b"]" * depth
    target = nest_template.encode("ascii").replace(needle, b'"admissible":' + nested, 1)
    _, duration = run_fresh(target, "nested-%d" % depth, must_refuse=True)
    assert duration < WALL_LIMIT_SECONDS, (depth, duration)

# Exact IEEE-754 integer boundary and adjacent encodings in every index-bearing category.
for index_value in (9007199254740991, 9007199254740992, 9007199254740993,
                    18446744073709551615, -1, 1.5, True, None):
    malformed = with_theorem(base, assumption)
    malformed["theorems"][0]["conclusion"] = index_value
    malformed_case(malformed, "root-index-%s" % str(index_value).replace(".", "_"))
for field, value in (("left", 9007199254740992), ("right", 18446744073709551615),
                     ("auxiliary", -1), ("children_start", 9007199254740991),
                     ("children_count", 9007199254740993)):
    malformed = with_theorem(base, assumption)
    malformed["kernel"]["nodes"][0][field] = value
    malformed_case(malformed, "node-%s-%s" % (field, value))
for child_value in (9007199254740992, 9007199254740993, 18446744073709551615, -1, True):
    malformed = with_theorem(base, assumption)
    malformed["kernel"]["children"] = [child_value]
    malformed_case(malformed, "child-index-%s" % child_value)

# Unknown node kind strings exercise the textual tag dispatch boundary on a theorem-reachable
# node; a well-formed outer package must still refuse without reporting any theorem replayed.
unknown_kind = with_theorem(base, assumption)
unknown_kind["kernel"]["nodes"][assumption["conclusion"]]["kind"] = "unknown-kind"
malformed_case(unknown_kind, "unknown-reachable-node-kind")

# Bounded-but-invalid ranges and out-of-arena references exercise checked arithmetic and
# child/index relationships before arena admission.
for start, count in ((len(base["kernel"]["children"]), 1),
                     (len(base["kernel"]["children"]) + 1, 0),
                     (2**53 - 1, 2), (len(base["kernel"]["children"]), 2**53 - 1)):
    malformed = with_theorem(base, assumption)
    malformed["kernel"]["nodes"][0]["kind"] = "array"
    malformed["kernel"]["nodes"][0]["children_start"] = start
    malformed["kernel"]["nodes"][0]["children_count"] = count
    malformed_case(malformed, "child-range-%d-%d" % (start, count))
for ref in (len(base["kernel"]["nodes"]), 2**53 - 1):
    malformed = with_theorem(base, assumption)
    malformed["kernel"]["nodes"][0]["kind"] = "binary"
    malformed["kernel"]["nodes"][0]["left"] = ref
    malformed_case(malformed, "node-ref-%d" % ref)

# A self-cycle in a reachable node and a two-node cycle must be refused without recursively
# overflowing statement construction, crashing, or hanging the fresh replay process.
for cycle_size in (1, 2):
    cyclic = with_theorem(base, assumption)
    nodes = cyclic["kernel"]["nodes"]
    cycle = len(nodes)
    for offset in range(cycle_size):
        nodes.append({"kind": "unary", "operator": "not", "left": cycle + ((offset + 1) % cycle_size),
                      "right": 0, "auxiliary": 0, "children_start": 0, "children_count": 0,
                      "value": "0", "name": "", "secondary_name": ""})
    theorem = copy.deepcopy(assumption)
    theorem["hypotheses"] = []
    theorem["hypothesis_origins"] = []
    theorem["conclusion"] = cycle
    cyclic["theorems"] = [theorem]  # Intentionally stale statement: force decoder path first.
    malformed_case(cyclic, "reachable-cycle-%d" % cycle_size, "arena-inadmissible")

# Forward references are legal JSON indexes but not a topologically valid source arena.
# Keep the theorem identity stale so the reader must classify the dependency safely.
forward = with_theorem(base, assumption)
forward_root = len(forward["kernel"]["nodes"])
forward["kernel"]["nodes"].append({"kind": "unary", "operator": "not", "left": forward_root + 1,
                                   "right": 0, "auxiliary": 0, "children_start": 0, "children_count": 0,
                                   "value": "0", "name": "", "secondary_name": ""})
forward["kernel"]["nodes"].append({"kind": "bool", "operator": "", "left": 0, "right": 0,
                                   "auxiliary": 0, "children_start": 0, "children_count": 0,
                                   "value": "1", "name": "", "secondary_name": ""})
forward["theorems"][0]["conclusion"] = forward_root
malformed_case(forward, "forward-reference", "arena-inadmissible")

# Near-budget parser workload: large escaped strings stay syntactically valid but violate
# the strict per-string bound. Enforce wall and CPU ceilings, and persist the compact seed on
# any timeout/crash instead of silently accepting an incomplete check.
large = with_theorem(base, assumption)
large["source"]["path"] = "x" * (8 * 1024 * 1024)
result, workload_seconds = run_fresh(large, "oversized-string", must_refuse=True)
assert workload_seconds < WALL_LIMIT_SECONDS, workload_seconds

print("R-006 structured package fuzz: hypothesis-cap exact/over shadow controls, positive replay "
      "control, 3 node text-schema mutations, "
      "5 nesting depths, 8 exact-index boundaries, 5 child-indexes, "
      "1 unknown reachable node tag, 4 child ranges, 2 node refs, 2 cycles, 1 forward ref, "
      "and 1 8-MiB parser workload passed; "
      "peak wall %.3fs, CPU %.3fs, RSS %d bytes (limits: %ds CPU, %d bytes RSS, %ds wall)" %
      (PEAK_WALL_SECONDS, PEAK_CPU_SECONDS, PEAK_RSS_BYTES, CPU_LIMIT_SECONDS,
       RSS_LIMIT_BYTES, WALL_LIMIT_SECONDS))
