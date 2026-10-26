# int_m2_bikemap: ride maps

<!-- quickstart:start -->
## Quick start

```bash
source ~/Desktop/Stripe/prep.sh   # once per terminal (or add this line to ~/.zshrc)
prep start int_m2_bikemap          # fresh copy + venv + install + first test run; starts the 60 min timer and cds you in
```

Then read `SPEC.md`, `DOCS.md` and start working. Everything below runs inside `~/Desktop/Stripe/scratch/int_m2_bikemap` with the venv active (`prep go int_m2_bikemap` gets you back there from a new terminal).

```bash
pytest -q                          # whole test suite
pytest -q -x                       # stop at the first failure
pytest -q --lf                     # rerun only the tests that failed last time
pytest -q tests/test_geo.py        # one file
pytest -q "tests/test_geo.py::test_zero_distance"
                                   # one test (copy ids from the failure output)
pytest -q -k "some_name"           # tests whose names match
pytest -q -s                       # show your print() output
pytest -x --pdb                    # open the debugger at the first failure
prep time                          # minutes used vs the limit
prep grade                         # when the timer is up: hidden acceptance tests for the parts you finished
prep reset int_m2_bikemap          # throw this attempt away and start over
```

Tips:
- At the `(Pdb)` prompt: `w` shows the call stack, `u`/`d` move up/down a frame, `p expr` prints, `n` next line, `s` step into, `c` continue, `ll` lists the function, `q` quits. `breakpoint()` in any line of code stops there too (remove it before you finish).
- The tests start their own copy of the mock API; you only need to run it yourself to explore.
- Print the raw JSON of one response before writing parsing code (`pytest -q -s` shows prints).
- Add your own tests in a new file under `tests/`; never edit the existing ones.

More test and debugger tricks: `~/Desktop/Stripe/CHEATSHEET.md`.
<!-- quickstart:end -->

## Goal

You maintain `bikemap`, a small Python library that turns rides recorded on bike computers into
maps and statistics using the Pathfinder maps API. Read `DOCS.md` (the API and the
ride file format) and `SPEC.md` (the task), then implement Part 1. Look at the raw
data first (`data/ride_canal_loop.geojson`, a landmarks page from the API) before
writing code.

Repository map:

- `bikemap/` - the library: models, geo helpers, timestamps, PNG helpers, error types
  (there is no HTTP client code yet: you write the API calls)
- `mock_map/` - local copy of the Pathfinder API (`python -m mock_map`)
- `data/` - a recorded ride and the landmarks served by the local API
- `scenarios/` - scenario files for the local API
- `tests/` - existing test suite

## Manual setup

Only needed if you do not use `prep start`:

```bash
cd ~/Desktop/Stripe
git clone practice/INTEGRATION/MEDIUM/int_m2_bikemap scratch/int_m2_bikemap && cd scratch/int_m2_bikemap
python3 -m venv .venv && source .venv/bin/activate
pip install --no-index --find-links ~/Desktop/Stripe/wheelhouse -r requirements.txt
python -m pytest -q
```

Run the local API in one terminal and try calls from another (the health endpoint
needs no key):

```
python -m mock_map
curl http://127.0.0.1:8700/v1/health
```

## Time limit

60 minutes in total: about 10 minutes for setup and reading, then about 45-50 minutes
of work. The spec has more parts than most people finish; get each part correct
before moving on.

## Rubric dimensions practiced

- Reading API docs carefully
- Authenticated HTTP calls and pagination
- Data modeling
- Correctness on edge cases
- Error handling
- Code structure
- Testing
- Communication (talk through decisions as you go)

## Rules

- Do not edit the existing tests. Add your own tests for the code you write.
- All five parts are in `SPEC.md`. Do them in order and finish (or decide to stop)
  one part before starting the next.
- Use only the standard library plus what `requirements.txt` lists (`requests` and
  `pytest`; no imaging libraries are needed: the API draws the image).
- After the timer ends, grade your work with
  `~/Desktop/Stripe/keys/grade.sh int_m2_bikemap <part>` (the last part you worked on).
  Open the keys folder only after the timer ends.
