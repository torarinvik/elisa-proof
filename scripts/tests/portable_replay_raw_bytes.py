"""Deterministic bounded raw-byte mutations of valid portable theorem packages.

Loaded by ``test_portable_replay.py`` after valid positive packages have replayed. Unlike
the structure-aware JSON matrix, mutations here operate only on the actual encoded bytes
fed to the standalone package decoder. This is deterministic boundary fuzzing, not
coverage-guided fuzzing.
"""
import hashlib
import json
from pathlib import Path
import random
import resource
import subprocess
import time

from portable_replay_support import *

CPU_LIMIT_SECONDS = 4
WALL_LIMIT_SECONDS = 5
RSS_LIMIT_BYTES = 512 * 1024 * 1024
OUTPUT_LIMIT_BYTES = 4 * 1024 * 1024
MINIMIZATION_ATTEMPTS = 24
MAX_MUTATIONS_PER_PACKAGE = 32
SEED_DIR = ROOT / "scripts/tests/r006_raw_byte_seeds"
CASE_DIR = WORK / "r006-raw-byte"
CASE_DIR.mkdir(parents=True, exist_ok=True)
PEAK_RSS = 0
PEAK_CPU = 0.0
PEAK_WALL = 0.0
RUNS = 0
MUTATIONS = 0
ACCEPTED_MUTATIONS = 0


class ChildFailure(AssertionError):
    def __init__(self, signature, message):
        super().__init__(message)
        self.signature = signature


def _cpu_total():
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    return usage.ru_utime + usage.ru_stime


def _limit_child():
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_LIMIT_SECONDS, CPU_LIMIT_SECONDS))


def _sample_rss(pid):
    sample = subprocess.run(["/bin/ps", "-o", "rss=", "-p", str(pid)],
                            capture_output=True, text=True, check=False, timeout=1)
    try:
        return int(sample.stdout.strip()) * 1024
    except ValueError:
        return 0


def bounded_replay(raw, label, expect_replay=False):
    """Run one exact byte stream with OS CPU and parent-enforced wall/RSS/output limits."""
    global PEAK_RSS, PEAK_CPU, PEAK_WALL, RUNS
    RUNS += 1
    digest = hashlib.sha256(raw).hexdigest()
    package_path = CASE_DIR / ("%s-%s.pkg" % (label, digest[:16]))
    stdout_path = CASE_DIR / ("%s-%s.stdout" % (label, digest[:16]))
    stderr_path = CASE_DIR / ("%s-%s.stderr" % (label, digest[:16]))
    package_path.write_bytes(raw)
    cpu_before = _cpu_total()
    started = time.monotonic()
    with stdout_path.open("wb") as stdout_file, stderr_path.open("wb") as stderr_file:
        child = subprocess.Popen([str(REPLAY), str(package_path)], stdout=stdout_file,
                                 stderr=stderr_file, preexec_fn=_limit_child)
        peak_rss = 0
        failure = None
        while child.poll() is None:
            elapsed = time.monotonic() - started
            peak_rss = max(peak_rss, _sample_rss(child.pid))
            if elapsed >= WALL_LIMIT_SECONDS:
                failure = ("timeout", "raw replay exceeded %ds wall limit" % WALL_LIMIT_SECONDS)
            elif peak_rss > RSS_LIMIT_BYTES:
                failure = ("rss-limit", "raw replay exceeded %d-byte RSS limit" % RSS_LIMIT_BYTES)
            elif stdout_path.stat().st_size + stderr_path.stat().st_size > OUTPUT_LIMIT_BYTES:
                failure = ("output-limit", "raw replay exceeded %d-byte output limit" % OUTPUT_LIMIT_BYTES)
            if failure:
                child.kill()
                child.wait()
                break
            time.sleep(0.01)
        returncode = child.wait()
    elapsed = time.monotonic() - started
    cpu_seconds = max(0.0, _cpu_total() - cpu_before)
    PEAK_RSS = max(PEAK_RSS, peak_rss)
    PEAK_CPU = max(PEAK_CPU, cpu_seconds)
    PEAK_WALL = max(PEAK_WALL, elapsed)
    if failure:
        raise ChildFailure(failure[0], "%s: %s (%s)" % (label, failure[1], digest))
    if stdout_path.stat().st_size > OUTPUT_LIMIT_BYTES or stderr_path.stat().st_size > OUTPUT_LIMIT_BYTES:
        raise ChildFailure("output-limit", "%s: raw replay output exceeded limit (%s)" % (label, digest))
    if returncode < 0 or returncode not in (0, 1):
        raise ChildFailure("crash", "%s: replay exited %d (%s)" % (label, returncode, digest))
    try:
        result = json.loads(stdout_path.read_bytes())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ChildFailure("invalid-output", "%s: no structured replay result (%s): %s" %
                           (label, digest, error)) from error
    if result.get("format") != "elisa-proof-replay-result-v1" or result.get("trust") != TRUST:
        raise ChildFailure("invalid-result", "%s: replay result identity/trust mismatch (%s)" %
                           (label, digest))
    summary = result.get("summary", {})
    total, accepted, refused_count = (summary.get("theorems"), summary.get("replayed"),
                                      summary.get("not_replayed"))
    if not all(isinstance(count, int) and not isinstance(count, bool) and count >= 0
               for count in (total, accepted, refused_count)) or total != accepted + refused_count:
        raise ChildFailure("partial-summary", "%s: inconsistent theorem summary (%s)" % (label, digest))
    theorem_results = result.get("theorems")
    if not isinstance(theorem_results, list) or len(theorem_results) != total:
        raise ChildFailure("partial-results", "%s: incomplete theorem result list (%s)" % (label, digest))
    replayed_results = sum(theorem.get("status") == "replayed" for theorem in theorem_results)
    if replayed_results != accepted:
        raise ChildFailure("partial-results", "%s: theorem result/summary mismatch (%s)" % (label, digest))
    if result.get("status") == "replayed":
        if returncode != 0 or total == 0 or refused_count != 0 or accepted != total:
            raise ChildFailure("partial-replay", "%s: replayed status without complete theorem replay (%s)" %
                               (label, digest))
    elif returncode != 1:
        raise ChildFailure("partial-replay", "%s: non-success package returned exit %d (%s)" %
                           (label, returncode, digest))
    if cpu_seconds > CPU_LIMIT_SECONDS or peak_rss > RSS_LIMIT_BYTES or elapsed > WALL_LIMIT_SECONDS:
        raise ChildFailure("resource-limit", "%s: observed resource limit exceeded (%s)" % (label, digest))
    if expect_replay and result.get("status") != "replayed":
        raise ChildFailure("positive-refusal", "%s: known-good package refused: %s" % (label, digest))
    return result


def _boundary_offsets(raw):
    """Choose deterministic offsets around JSON grammar and package-schema boundaries."""
    offsets = {0, len(raw) // 2, max(0, len(raw) - 1)}
    for token in (b'"format"', b'"kernel"', b'"nodes"', b'"children"', b'"theorems"',
                  b'"conclusion"', b'"statement"', b'"goal_fingerprint"'):
        start = 0
        while len(offsets) < 48:
            found = raw.find(token, start)
            if found < 0:
                break
            offsets.update((found, found + len(token) // 2, found + len(token) - 1))
            start = found + len(token)
    for byte in (b"{", b"}", b"[", b"]", b'"', b":", b",", b"\\"):
        found = raw.find(byte)
        if found >= 0:
            offsets.add(found)
            offsets.add(min(len(raw) - 1, found + 1))
    return sorted(offset for offset in offsets if 0 <= offset < len(raw))


def mutations(raw, seed_index):
    """Yield a reproducible set of truncation, insertion, deletion, and byte substitutions."""
    rng = random.Random(0xE115A + seed_index)
    offsets = _boundary_offsets(raw)
    candidates = [("trailing-nul", raw + b"\x00"), ("trailing-invalid-utf8", raw + b"\xff"),
                 ("trailing-token", raw + b"x"), ("leading-bom", b"\xef\xbb\xbf" + raw),
                 ("leading-nul", b"\x00" + raw)]
    first_quote = raw.find(b'"')
    if first_quote >= 0:
        candidates.append(("invalid-string-escape", raw[:first_quote + 1] + b"\\q" + raw[first_quote + 1:]))
    for offset in sorted(set((0, 1, len(raw) // 4, len(raw) // 2, (3 * len(raw)) // 4, len(raw) - 1))):
        if 0 <= offset < len(raw):
            candidates.append(("truncate-%d" % offset, raw[:offset]))
    for offset in offsets:
        original = raw[offset]
        for label, byte in (("zero", 0), ("ff", 255), ("nul", 0), ("flip-high", original ^ 0x80)):
            if byte != original:
                candidates.append(("replace-%s-%d" % (label, offset), raw[:offset] + bytes((byte,)) + raw[offset + 1:]))
        candidates.append(("delete-%d" % offset, raw[:offset] + raw[offset + 1:]))
        for label, byte in (("brace", ord("}")), ("quote", ord('"')), ("comma", ord(",")),
                            ("slash", ord("\\")), ("utf8", 0xFF)):
            candidates.append(("insert-%s-%d" % (label, offset), raw[:offset] + bytes((byte,)) + raw[offset:]))
    # Fixed-seed substitutions add coverage outside named keys without making runs flaky.
    for index in range(min(8, len(raw))):
        offset = rng.randrange(len(raw))
        candidates.append(("seeded-%02d-at-%d" % (index, offset),
                           raw[:offset] + bytes((raw[offset] ^ (1 << rng.randrange(8)),)) + raw[offset + 1:]))
    seen = set()
    unique = []
    for label, candidate in candidates:
        if candidate and candidate != raw and candidate not in seen:
            seen.add(candidate)
            unique.append((label, candidate))
    if len(unique) <= MAX_MUTATIONS_PER_PACKAGE:
        yield from unique
        return
    # Spread the fixed budget over the complete deterministic candidate sequence. This
    # retains late schema-key and seeded-offset cases instead of over-sampling the prefix,
    # while always exercising invalid UTF-8, NUL, BOM, trailing-token, and escape boundaries.
    mandatory = unique[:6]
    remaining = unique[6:]
    budget = MAX_MUTATIONS_PER_PACKAGE - len(mandatory)
    indexes = sorted({(index * (len(remaining) - 1)) // (budget - 1)
                      for index in range(budget)})
    for item in mandatory:
        yield item
    for index in indexes:
        yield remaining[index]


def _failure_signature(raw, label):
    try:
        bounded_replay(raw, "min-%s" % label)
    except ChildFailure as error:
        return error.signature
    return None


def minimize(raw, signature, label):
    """Try at most 24 chunk deletions; preserve the same failure class and byte provenance."""
    current = raw
    attempts = 0
    chunk = max(1, len(current) // 2)
    while chunk and attempts < MINIMIZATION_ATTEMPTS:
        start = 0
        changed = False
        while start < len(current) and attempts < MINIMIZATION_ATTEMPTS:
            candidate = current[:start] + current[start + chunk:]
            if candidate and len(candidate) < len(current):
                attempts += 1
                if _failure_signature(candidate, label) == signature:
                    current = candidate
                    changed = True
                    break
            start += chunk
        if not changed:
            chunk //= 2
    return current


def retain_failure(raw, label, signature, message):
    SEED_DIR.mkdir(parents=True, exist_ok=True)
    minimized = minimize(raw, signature, label)
    digest = hashlib.sha256(minimized).hexdigest()
    (SEED_DIR / ("%s-%s.bin" % (label, digest[:16]))).write_bytes(minimized)
    metadata = {"label": label, "failure_signature": signature, "sha256": digest,
                "original_bytes": len(raw), "minimized_bytes": len(minimized), "message": str(message)}
    (SEED_DIR / ("%s-%s.json" % (label, digest[:16]))).write_text(
        json.dumps(metadata, sort_keys=True, indent=2) + "\n")


def _encode(package):
    return json.dumps(package, ensure_ascii=True, separators=(",", ":")).encode("ascii")


# Re-run all known-good packages through the bounded raw-byte path: the mutated inputs are
# grounded in exactly these encoded certificates and every positive control must remain valid.
for package_index, (package_name, package) in enumerate(packages.items()):
    encoded = _encode(package)
    positive = bounded_replay(encoded, "positive-%02d" % package_index, expect_replay=True)
    assert positive["summary"]["theorems"] == len(package["theorems"]), package_name
    for mutation_index, (mutation_name, raw) in enumerate(mutations(encoded, package_index)):
        label = "p%02d-m%03d-%s" % (package_index, mutation_index, mutation_name)
        try:
            result = bounded_replay(raw, label)
        except ChildFailure as error:
            retain_failure(raw, label, error.signature, error)
            raise
        MUTATIONS += 1
        if result["status"] == "replayed":
            ACCEPTED_MUTATIONS += 1

print("R-006 raw-byte mutation: %d encoded positive packages replayed; %d deterministic byte mutations "
      "checked (%d remained valid); %d fresh bounded decoder runs, peak wall %.3fs, CPU %.3fs, RSS %d bytes; "
      "limits %ds CPU/%ds wall/%d bytes RSS/%d bytes output; no crashes or partial theorem replay" %
      (len(packages), MUTATIONS, ACCEPTED_MUTATIONS, RUNS, PEAK_WALL, PEAK_CPU, PEAK_RSS,
       CPU_LIMIT_SECONDS, WALL_LIMIT_SECONDS, RSS_LIMIT_BYTES, OUTPUT_LIMIT_BYTES))
