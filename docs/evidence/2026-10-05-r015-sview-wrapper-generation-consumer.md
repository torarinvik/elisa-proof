# R-015 sview wrapper provenance consumer

`test_sview_wrapper_provenance.py` now imports the shared portable replay support module. That
module resolves the producer and replay executable together from one published generation, and
the test uses those pinned paths for source reports, package production, valid replay, and forged
package replay. The report assertions, package replay checks, forgery checks, and lifetime controls
remain unchanged.

Validation: `python3 scripts/tests/test_portable_replay_generation_resolution.py` passed. The
focused sview script could not run because this checkout has no `build/elisa-proof-generations`
directory or published product pair; shared resolution correctly refused to select binaries.
