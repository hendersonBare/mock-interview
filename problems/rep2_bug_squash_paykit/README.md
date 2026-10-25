# paykit

`paykit` is a small, standard-library-only Python toolkit a merchant uses to talk to
a card payment gateway: an HTTP client with retries, idempotency keys and cursor
pagination, an integer minor-unit `Money` type with currency conversion, webhook
signature verification with event dispatch, and an in-memory ledger of charges and
refunds.

<!-- quickstart:start -->
## Quick start

```bash
source ~/Desktop/Stripe/prep.sh   # once per terminal (or add this line to ~/.zshrc)
prep start rep2_bug_squash_paykit  # fresh copy + venv + install + first test run; starts the 60 min timer and cds you in
```

Then read `ISSUE.md` and start working. Everything below runs inside `~/Desktop/Stripe/scratch/rep2_bug_squash_paykit` with the venv active (`prep go rep2_bug_squash_paykit` gets you back there from a new terminal).

```bash
pytest -q                          # whole test suite
pytest -q -x                       # stop at the first failure
pytest -q --lf                     # rerun only the tests that failed last time
pytest -q tests/test_gateway.py    # one file
pytest -q "tests/test_gateway.py::test_create_charge_returns_succeeded_charge"
                                   # one test (copy ids from the failure output)
pytest -q -k "some_name"           # tests whose names match
pytest -q -s                       # show your print() output
pytest -x --pdb                    # open the debugger at the first failure
prep time                          # minutes used vs the limit
prep grade                         # when the timer is up: hidden acceptance tests
prep reset rep2_bug_squash_paykit  # throw this attempt away and start over
```

Tips:
- At the `(Pdb)` prompt: `w` shows the call stack, `u`/`d` move up/down a frame, `p expr` prints, `n` next line, `s` step into, `c` continue, `ll` lists the function, `q` quits. `breakpoint()` in any line of code stops there too (remove it before you finish).
- Pick ONE failing test, rerun only it while you investigate, then run the whole suite at the end.
- Symptom far from the cause: `pytest -x --pdb`, then `u` repeatedly until you find the frame where the value first goes wrong.
- `git diff` before you say you are done: the change should be small and explainable. `git stash` / `git stash pop` compares behaviour with and without it.

More test and debugger tricks: `~/Desktop/Stripe/CHEATSHEET.md`.
<!-- quickstart:end -->

## Goal

The last round of changes left the toolkit in poor shape. A large part of the test
suite is red, and users have filed the reports collected in `ISSUE.md`, grouped by
area (gateway client, money and currency, webhooks, ledger).

Get the whole suite green by changing the library code under `paykit/`. Work the way
you would in the interview: run the suite and read the failures as a map, take one
failing test at a time, reproduce it and look at the real values, make the smallest
change that explains them, then re-run.

Layout:

```
data/      charges.json (sandbox charges served by the fake gateway), fx_rates.json (units per 1 USD)
paykit/    the library: errors, fx, gateway, ledger, models, money, webhooks
tests/     the pytest suite; dummy_gateway.py is an in-process fake gateway speaking real HTTP
ISSUE.md   reports from users of the toolkit
```

Amounts are always integers in the currency's minor unit: cents for USD, EUR and
GBP, whole yen for JPY (no minor unit), fils for KWD (three decimal places).

## Manual setup

Only needed if you do not use `prep start`:

```bash
cd ~/Desktop/Stripe
git clone practice/BUG_SQUASH/MEDIUM/rep2_bug_squash_paykit scratch/rep2_bug_squash_paykit && cd scratch/rep2_bug_squash_paykit
python3 -m venv .venv && source .venv/bin/activate
pip install --no-index --find-links ~/Desktop/Stripe/wheelhouse -r requirements.txt
python -m pytest -q
```

The package is imported straight from this folder (`pythonpath = .` in `pytest.ini`);
nothing is installed except pytest. The suite runs in about a second.

- `python -m pytest -q -s tests/test_gateway.py` also prints every request the fake
  gateway receives (`METHOD path -> status`).
- `python tests/dummy_gateway.py` starts the fake gateway on a free port so you can
  poke at it by hand; it prints the URL and the test API key.

## Time limit

60 minutes: about 10 minutes to set up and read, then 45-50 minutes of work. It is
normal not to reach a fully green suite; how you choose what to work on next is part
of the exercise.

## Rubric dimensions practiced

- Debugging methodology: reproduce, form a hypothesis, confirm it, then change code.
- Reading tests as the specification, including the fake gateway under `tests/`.
- Navigating several small modules and an HTTP boundary you have never seen.
- Prioritizing when many tests fail at once: grouping failures and picking an order.
- Minimal, targeted changes that keep the passing tests passing.
- Communication: say what you see, what you suspect and why, as you go.

## Rules

- The tests are the spec. Never edit or delete existing tests (including
  `tests/dummy_gateway.py`) or the files under `data/`, and do not change
  `pytest.ini`. Adding NEW tests in a new file under `tests/` is fine.
- Change only the library code under `paykit/`. Keep changes small and local; do not
  rewrite modules.
- Do not add, upgrade or swap dependencies, and do not compare against an installed
  or downloaded copy of anything.
- Use git freely (`git diff`, `git grep`, `git stash`). The repository has a single
  commit, so history will not help.
- After the timer ends you can check your work with
  `~/Desktop/Stripe/keys/grade.sh rep2_bug_squash_paykit all <path to your clone>`.
  Only open the keys folder after the timer ends.
