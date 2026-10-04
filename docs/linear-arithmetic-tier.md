# Design note: a general linear-arithmetic tier

Status: implemented in `src/proof/linear/linear_arithmetic.elisa` (producer) and `src/proof/kernel_replay/linear_arithmetic.elisa` (kernel). Atoms are names only; call terms are not yet admitted. The kernel re-runs the elimination and accepts only a contradiction whose multipliers pass the Farkas check against the original rows.

## Motivation

The remaining mocap-cleaner laws fail on goals that are linear but fall outside
the existing tiers. The difference tier handles one unit name per side. The
scaled tier handles one name with a coefficient. Examples:

- `accel`: `prev - 2*now + next` is bounded by `4*LIMIT` from the three input intervals.
- `ballistic_residual`, `side`, `magnitude_of_positive`, `limit_wring`: the same pattern.
- The wrap-guard facts in `small_step_passes` and `zero_cap_freezes`: `origin + cap`
  must be shown not to overflow from relational facts.
- Disjunctive summaries such as `soften` have five ensures and 32 case splits,
  which exceeds the budget. Each branch is a small linear problem, so a decision
  procedure that settles them cheaply also lets the splitter prune them.

## Scope

- **Input:** a conjunction of facts and one goal. Each is a comparison
  (`<`, `<=`, `==`, `!=` as two cases, `>=`, `>`) between integer affine forms
  `c0 + sum(ci * xi)`.
  - The `ci` are literals.
  - The `xi` are names, field places, or witnessed call terms. Call terms are
    abstracted to fresh atoms, as the place rule already does.
- **Not in scope:** nonlinear products of names, division (except the existing
  floor-quotient facts), modular reasoning, quantifiers, and floats.
- **Size caps:** at most 8 atoms and 24 constraints. Anything larger is declined
  with a gate label (`linear-budget`), never approximated.
- **Where it runs:** after the difference and scaled tiers, and before the case
  splitter gives up. The splitter can call it to discharge or prune branches.

## Procedure

1. Negate the goal and add it to the facts. Over the integers, `a < b` becomes
   `a - b + 1 <= 0`. An equality goal becomes two refutations.
2. Run Fourier–Motzkin elimination over the rationals, one atom at a time, with
   exact `i64` arithmetic. Every product and sum is checked, and any overflow
   declines the goal.
3. The goal is proven when a `0 <= -k` constraint with `k > 0` is derived.
4. Rational infeasibility implies integer infeasibility, so a refutation is
   sound. The procedure is incomplete for integer-only infeasibility, and that
   is accepted: it declines rather than guesses.

## Soundness

- **Width.** Every fact and the goal must first pass the existing ambiguity and
  wrap guards. The tier then reasons over mathematical integers, and that is
  only valid when every operation in the source was shown not to wrap at its
  declared width. The tier never proves a wrap guard by assuming the absence
  of wrap.
- **Atoms.** A call term is admitted as an atom only when it has a pure-call
  witness. Otherwise two occurrences might denote different values.
- **Arithmetic.** All coefficient arithmetic goes through `proof_add_safe` and
  `proof_mul_safe`, and any failure declines. Combination multipliers are
  positive, and are reduced by their gcd before use.
- **Trust.** Nothing new is trusted. The producer emits a certificate, and the
  kernel checks it without searching.

## Kernel rule: checking a Farkas certificate

The producer records a certificate. It lists, for each fact used and for the
negated goal, the fact index and a non-negative integer multiplier `λi`.

For each listed item, the kernel:

1. normalises the item to `ai·x + bi <= 0`, reusing the collector mirrored in
   `kernel_replay/normalized_differences.elisa`, extended to literal
   coefficients;
2. checks that each `λi >= 0`, and that `λi` is `> 0` for the negated goal;
3. computes `Σ λi·ai` with checked arithmetic and requires it to be the zero
   vector;
4. computes `Σ λi·bi` and requires it to be `> 0`.

Together these give `0 < Σ λi·bi <= 0`, a contradiction, so the goal holds.

Kernel cost is linear in the certificate. The kernel repeats the same width and
wrap checks on every item as the producer, so a certificate cannot introduce an
unchecked operation. The rule is a new `linear-farkas` certificate kind,
mirrored in the certificate schema and the replay dispatcher.

## Tests

### Disequality and correlated cases

`a != b` can also close by temporarily assuming `a == b` and using the existing linear
disequality-refutation procedure. The primitive comparison and both the original premises and
goal must pass machine-width guards first. Replay constructs and checks the same temporary
equality independently; no unchecked producer result is admitted. This retains the existing
atom, constraint, and arithmetic limits.

For disjunctive goals with correlated premises, split the relevant premise before spending
search fuel on an alternative that cannot hold in every case. Parentheses under a negated
conjunction are transparent to that split. Both cases must establish the whole goal; one case
alone is not a proof. `scripts/test_correlated_disjunction.py` pins the positive and false
controls, including an unsafe wrapping goal and independent portable replay.

The separate closed-width rule in `kernel_replay/closed_width_formulas.elisa` accepts an OR
formula only when exact closed evaluation is true at every signed/unsigned integer width.
It never generalizes affine reasoning to arbitrary wrapping premises.

- **Accepted:** the `accel` bound, the `origin + cap` wrap guard, and a
  three-name chain.
- **Rejected controls:** an off-by-one bound, a certificate with a negative
  multiplier, a certificate whose coefficients do not cancel, and a goal needing
  integer-only reasoning (`2x == 1`), which must decline.

## Estimate

- Producer: about 400 lines.
- Kernel: about 200 lines.
- Examples and dogfood registration.

Most of the risk is in making the certificate format and the fact-index
stability survive case splitting.
