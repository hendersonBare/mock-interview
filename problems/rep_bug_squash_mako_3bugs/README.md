# Mako: three user reports

<!-- quickstart:start -->
## Quick start

```bash
source ~/Desktop/Stripe/prep.sh   # once per terminal (or add this line to ~/.zshrc)
prep start rep_bug_squash_mako_3bugs     # fresh copy + venv + install + first test run; starts the 60 min timer and cds you in
```

Then read `ISSUE.md` and start working. Everything below runs inside `~/Desktop/Stripe/scratch/rep_bug_squash_mako_3bugs` with the venv active (`prep go rep_bug_squash_mako_3bugs` gets you back there from a new terminal).

```bash
pytest -q                          # whole test suite
pytest -q -x                       # stop at the first failure
pytest -q --lf                     # rerun only the tests that failed last time
pytest -q test/test_ast.py         # one file
pytest -q "test/test_ast.py::AstParseTest::test_locate_identifiers"
                                   # one test (copy ids from the failure output)
pytest -q -k "some_name"           # tests whose names match
pytest -q -s                       # show your print() output
pytest -x --pdb                    # open the debugger at the first failure
prep time                          # minutes used vs the limit
prep grade                         # when the timer is up: hidden acceptance tests
prep reset rep_bug_squash_mako_3bugs # throw this attempt away and start over
```

Tips:
- At the `(Pdb)` prompt: `w` shows the call stack, `u`/`d` move up/down a frame, `p expr` prints, `n` next line, `s` step into, `c` continue, `ll` lists the function, `q` quits. `breakpoint()` in any line of code stops there too (remove it before you finish).
- Pick ONE failing test, rerun only it while you investigate, then run the whole suite at the end.
- Symptom far from the cause: `pytest -x --pdb`, then `u` repeatedly until you find the frame where the value first goes wrong.
- `git diff` before you say you are done: the change should be small and explainable. `git stash` / `git stash pop` compares behaviour with and without it.

More test and debugger tricks: `~/Desktop/Stripe/CHEATSHEET.md`.
<!-- quickstart:end -->

## Goal

This repository is a vendored copy of [Mako](https://github.com/sqlalchemy/mako),
the Python template engine. Three separate user reports, collected in
`ISSUE.md`, describe problems in three unrelated areas of the engine. The
existing unit test suite is large and fine-grained; use it to narrow the
search.

Your task: find the root causes in the library code and fix them so that

- the behaviour described in each report in `ISSUE.md` is correct, and
- the complete existing test suite passes.

Aim for small, targeted changes. Be ready to explain how you found each
problem and why your change is the right one. Fixing two of three cleanly
and explaining them well beats three rushed changes.

## Manual setup

Only needed if you do not use `prep start`:

```bash
cd ~/Desktop/Stripe
git clone practice/BUG_SQUASH/MEDIUM/rep_bug_squash_mako_3bugs scratch/rep_bug_squash_mako_3bugs && cd scratch/rep_bug_squash_mako_3bugs
python3 -m venv .venv && source .venv/bin/activate
pip install --no-index --find-links ~/Desktop/Stripe/wheelhouse -r requirements.txt
python -m pytest -q
```

Mako is imported straight from this folder (run pytest from the repository
root); it is not installed. The test configuration lives in `setup.cfg`
(`[tool:pytest]`). Three upstream tests whose expected HTML depends on the
exact Pygments release are switched off there; that is environment, not part
of the exercise. The suite runs in about ten seconds.

## Time limit

60 minutes: about 10 minutes for setup and reading, then roughly 45-50 minutes
of debugging. Stop when the timer ends, even if something is still failing.

## Rubric dimensions practiced

- Navigating a large, idiomatic code base you have never seen: lexer, parse
  tree, code generator, runtime and lookup
- Using failing unit tests and small reproductions to localize a problem
  quickly, then confirming the hypothesis before changing code
- Reading generated code: Mako turns each template into a Python module, and
  `Template(...).code` shows it
- Making minimal, well-scoped fixes without collateral changes
- Prioritizing under time pressure and communicating: state hypotheses out
  loud, explain what each experiment showed, summarize each fix in one or two
  sentences

## Rules

- The tests are the spec. Never edit or delete existing tests (and do not
  change the pytest settings in `setup.cfg`). Adding NEW tests in a new file
  under `test/` is fine.
- Change only the library code under `mako/`.
- Do not upgrade or swap dependencies, and do not compare against a downloaded
  or installed copy of Mako.
- Any tooling is fine: a debugger, print statements, `git diff`, `git grep`,
  `git stash`. The repository has a single commit, so history will not help.
- After the timer ends you can check your work with
  `~/Desktop/Stripe/keys/grade.sh rep_bug_squash_mako_3bugs all <path to your clone>`.
  Only open the keys folder after the timer ends.
