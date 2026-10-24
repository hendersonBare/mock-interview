# Interviewer materials (spoilers)

```
solutions/
  grade.sh                       hidden acceptance tests runner
  rep_bug_squash_mako_3bugs/
    KEY_BUGS.md                  the 3 bugs: root cause, minimal fix, how a good candidate finds each
    KEY_FOLLOWUPS.md             follow-up questions for the last 5-10 min, with good answers
    reference.patch              all 3 fixes (apply to a clean copy of the problem)
    patches/                     the planted bugs, one per file (the reverse of each fix)
    hidden_tests/                32 acceptance tests
  int_m2_bikemap/
    KEY_SOLUTION.md              the trap, expected outputs per part, graded edge cases
    parts/                       spec parts 2-5 (+ extra data/scenario files) to hand out
    patches/part<k>.patch        reference solution after part k (reference.patch = part 5)
    hidden_tests/                51 acceptance tests, split by part (p1..p5)
```

Both reference solutions were checked against a fresh copy of `problems/`. Mako: 517 visible
and 32 hidden tests pass. BikeMap: 50 visible and 51 hidden tests pass through Part 5.

## Bug Squash: Mako

1. Before the round, read `KEY_BUGS.md` (10 min). Point the candidate at `README.md` and
   `ISSUE.md`.
2. Starting state is 6 failing tests, 2 per bug (one new scenario test and one upstream
   regression test).
3. **Hint ladder** (give one step at a time, only after ~5 min stuck on a bug, and note each
   hint on the scorecard):
   - **B, lookup (easiest):** "What does the traceback say about the path being opened?" →
     "Walk up to `TemplateLookup.get_template`." → "What's the difference between `exists` and
     `isfile`?"
   - **A, lambda default:** "Look at the Python Mako generated: `print(Template(src).code)`." →
     "Where are `<%def>` argument defaults turned back into source?" (`mako/_ast_util.py`) →
     "Which AST node holds a lambda parameter, and does it have a `visit_` method?"
   - **C, comment-only elif (hardest):** "Which of the `test_commented_blank_control_*` tests
     fail, and what's different about that one?" → "Why would Python need a `pass` here?" →
     "Find where codegen emits `pass` (`grep -n '\"pass\"' mako/codegen.py`)."
4. Use `KEY_FOLLOWUPS.md` for the last few minutes or if they finish early.

## Integration: BikeMap

1. Before the round, read `KEY_SOLUTION.md` (10 min) and skim `../problems/int_m2_bikemap/DOCS.md`.
2. Only Part 1 is in `SPEC.md`. When the candidate finishes a part (or you decide to move on),
   hand them the next one. Either:
   - run the bundled reveal script inside *their* working copy, pointing it at this folder:
     ```bash
     STRIPE_PREP_KEYS=/path/to/this/repo/solutions python reveal.py 2   # then 3, 4, 5
     ```
     It appends the part to `SPEC.md` and copies in that part's extra data and scenario files;
   - or paste `parts/part<k>.md` into the chat and send them the files in `parts/part<k>_files/`.
3. **Don't mention the lon/lat trap.** Catching it from `DOCS.md` is part of the evaluation. If
   they render in Part 2 without noticing, you can ask "how would you check the map was drawn
   in the right place?" once, and note that you did.
4. Typical candidates finish Parts 1-3. Part 4 or 5 is a strong signal.

## Grading after the timer

Run the hidden tests against the candidate's working copy (it needs its `.venv` with the
requirements installed):

```bash
solutions/grade.sh rep_bug_squash_mako_3bugs all /path/to/candidate/mako-copy
solutions/grade.sh int_m2_bikemap 3 /path/to/candidate/bikemap-copy   # parts 1..3 cumulatively
```

It prints `RESULT: PASS/FAIL` plus the candidate's visible-suite result. Use it as the
correctness input to the scorecards in the top-level `README.md`, alongside your notes on
process and communication.

To see a reference solution yourself:

```bash
cp -R problems/int_m2_bikemap /tmp/bike-ref && cd /tmp/bike-ref
STRIPE_PREP_KEYS=<repo>/solutions python reveal.py 5
git init -q && git apply <repo>/solutions/int_m2_bikemap/reference.patch
```
