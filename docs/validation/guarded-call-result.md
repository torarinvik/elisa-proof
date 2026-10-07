# Local call result after an early-return guard

`guarded_call_result_bound.elisa` minimizes the engine audio-music replay
failure. A checked bounded function initializes an immutable local after
an early-return guard. The previous source walk rejected the earlier return
arm even though only the continuing path reaches that local declaration.

The fix recognizes only an earlier if with one empty arm and one sole return.
It imports no branch facts and leaves exact call-site, owner, local declaration,
argument and callee-summary validation in place. Loops, arbitrary transfers
and branches with declarations retain their existing restrictions.

The accepted fixture fully replays; the invalid bound of 9999 is refused
(the cap can return 10000). The existing call-result-width suite and all seven
conditional-source cases pass. The uncached engine sweep passes 66/73:
`audio_music` is restored, and seven other rows remain failing. The full
prover matrix is still unverified. Logs in engine build/validation:
`prover-guarded-call-build.log`, `proof-guarded-call-full-sweep.log`.
