# R-007 finite quantifier binder escape check

This focused kernel runtime regression checks that a finite universal binder does not act as an
outer-scope witness. The positive control independently replays `forall x in [1]: x == 1`. The
adversarial goal then asks the kernel to prove free `x == 1` from that quantified proposition;
independent goal replay must refuse it. The executable harness completed with exit 0, so both
expectations held. No soundness defect was observed in this finite universal path.

## Validation identity

- Proof source revision: `8ef1d760c5ba7aefcae1b571c7235f7ed72c1653`, based on committed `main`
  `d0b946d6002b6b11b221cbe24c5b16df9e6fbe16`.
- Pinned Stage1 revision: `7b27fa312c5af923f044f6ee0e5e1de4f811f595`; compiler binary SHA-256
  `f77278c716dea7f3dba8f4fcbcf76ecc473426ab3f163c95fea4e358f6337653`.
- Runtime object SHA-256:
  `b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897`.
- `examples/kernel_arena_runtime.elisa` compiled at O0. Object SHA-256:
  `7f0e4e6fc512ef38691cc146d3a640cabb3cda9a42a2ed75bda086fd851b7520`.
- Linked and ran the kernel arena harness (exit 0). Executable SHA-256:
  `a851d9459cce46a916de978441e6d976d0ca83bb2bfd85a946b537e2ba054d26`.
- `git diff --check`: passed.

This tests finite universal enumeration against one free-name escape attempt. Quantifier binders
are still represented by names rather than stable binder IDs. This does not test alpha-renaming,
same-spelled nested binders generally, eigenvariable rules for a proof calculus with quantifier
introduction, sibling branch escape, or post-validation arena mutation.
