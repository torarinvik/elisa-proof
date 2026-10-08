# Match payload widening replay (2026-10-08)

The frozen `ee9c67a9` full matrix fails `test_widening_cast.py`: `wide_first`
produces 36 certificates but only 35 replay. Its cast equation is
`wide == __elisa_rebind_0`. The declaration validator rejected the internal
receiver before reaching its existing match-arm validator.

The source change routes internal receivers directly through that validator.
Ordinary parameter validation remains separate. The match validator still
requires the unique source arm, immutable enum subject, exact payload ordinal,
range-preserving builtin conversion, unchanged payload, and consuming return.
No certificate is admitted from a symbol spelling alone.

## Focused source admission

Run `scripts/test_match_widening_source.py` with compiler `52d60fcf` and its
matching Stage1 product, bounded to 3 GiB / 360 seconds. Result: status 0,
32.06 seconds, 1,367,088 KiB peak RSS. The authentic equation is accepted;
12 forged trace/source controls are refused. Controls cover wrong line,
receiver and target; narrowing, mutable target, wrong cast method/payload,
payload shadow/write, mutable subject, prior fresh witness and changed return
path. The harness is registered beside the widening-cast matrix test.

Evidence: engine `build/validation/match-widening-source-controls.log` and its
watchdog JSON. Product replay, portable replay and engine sweep still require
qualification on a clean paired build. This source admission result does not
establish full matrix compatibility or repair quantified branch consequences.

The existing 601-line invariant harness is restored to the 600-line policy by
joining its final print opening line; its assertions are preserved.
