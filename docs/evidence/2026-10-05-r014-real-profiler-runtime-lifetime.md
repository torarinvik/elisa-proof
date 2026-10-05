# R-014: real profiler runtime/allocation-lifetime probe

## Result

The probe builds the native Elisa profiler in a temporary directory, compiles
[`examples/proof_allocation_lifetime.elisa`](../../examples/proof_allocation_lifetime.elisa)
with the compiler checkout's Stage1, links the matching runtime and profiler
collector, then captures and analyzes one real target execution. Products,
capture JSON, sidecars, compiler logs, and analyzer inputs are isolated beneath
an automatically removed temporary directory. No profiler or compiler source
was changed for this probe.

The captured repetition completed with exit status zero and a complete framed
capture. Allocation-hook ABI evidence was exact v1 negotiation plus v1 calls;
there were no legacy calls, rejected versions, or dropped allocation records.
Observed runtime event kinds were:

| Runtime record | Count |
| --- | ---: |
| `alloc` | 4 |
| `reclaim` | 1 |
| `region_create` | 2 |
| `region_reset` | 1 |
| `region_free` | 4 |

The fixture explicitly requests arena allocations of 32 and 64 bytes, reclaims
the 32-byte span, reuses its address for a 16-byte request, and resets the same
arena afterward. The test matches the reclaim to the original allocation and
checks that reuse and reset occur at the same arena identity and in sequence.
The probe also returns an `sview` from a helper with the source region's
lifetime, reads the returned view while that region is alive, then destroys the
region. The target exits successfully. This tests that safe usage path; the
profiler emits no separate `sview`-lifetime event and the capture does not prove
the compiler's general borrow-safety rules.

The profiler's production allocation-lifetime analyzer returned available
metrics for this capture:

| Metric | Observation |
| --- | ---: |
| Peak logical live bytes | 256 bytes |
| Logical live bytes at capture end | 0 bytes |
| Peak observed backing capacity | 1,050,624 bytes |
| Observed backing capacity at capture end | 0 bytes |
| Maximum capacity retained after reset | 1,048,576 bytes |
| Post-reset reuse boundaries observed | 0 |
| Peak target RSS | 2,113,536 bytes |

Logical live bytes are reconstructed from observed arena events and their
retirement semantics. Backing capacity is arena region capacity and is not
committed memory. Peak RSS is an independent OS process measurement. These
figures must not be added, substituted for one another, or interpreted as a
heap census. In particular, the large retained-after-reset observation is not
a leak claim; the explicit arena is freed before capture ends.

Instrumentation overhead is unavailable: this probe does not have a matched
uninstrumented executable built from identical source, compiler, flags, and
runtime, so it reports no overhead estimate.

## Toolchain identity and validation

- Compiler checkout: `../Elisa-compiler`, revision
  `bc8def2eadf41dd088adce22b4d3d9e74aadfee9`, clean when checked.
- Stage1 product: `../Elisa-compiler/bin/elisac-stage1`, SHA-256
  `96eca8200bb268ea5cc1635a66d6b0da0cd85611331319c3227362d9421c2947`.
- Stage1 provenance command:
  `python3 ../Elisa-compiler/scripts/stage1_provenance.py check ../Elisa-compiler ../Elisa-compiler/bin/elisac-stage1`
  reported `stage1 provenance: current` for the revision above.
- Matching Stage1 runtime object SHA-256:
  `b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897`.
- Profiler checkout: `../elisa-profiler`, revision
  `39f46e4983c4e233b542e7c57ff27f15c96fb8e2`, clean when checked.
- Profiler allocation collector source SHA-256:
  `10faf3cb42514c5750e1d1b517e07222a75e94ff993e6794d224d54ea967ef80`.
- Probe source SHA-256:
  `a750ccd4f3249d9bed304fe5bbabb3d3a8135aa440035dbb74987d00d2d0c470`.

Validation command:

```sh
ELISA_COMPILER_ROOT="$PWD/../Elisa-compiler" \
ELISA_STAGE1_BIN="$PWD/../Elisa-compiler/bin/elisac-stage1" \
ELISA_RUNTIME_OBJ="$PWD/../Elisa-compiler/build/runtime/elisacore_runtime.o" \
python3 scripts/tests/test_profiler_runtime_lifetime.py
```

It rebuilt the profiler through `scripts/build-native.sh` at O2, ran the live
capture, and passed all assertions. Python bytecode validation, shell syntax,
and `git diff --check` also passed. This is one bounded runtime capture; it does
not establish complete coverage of every allocator path, every lifecycle path,
or post-shutdown operations.
