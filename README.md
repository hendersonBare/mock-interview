# Stripe mock interview: Bug Squash + Integration

Thanks for running this mock. This repo has everything you need to play the interviewer for two
Stripe-style onsite rounds:

| Round | Problem | Folder | Time |
|---|---|---|---|
| Bug Squash | Mako template engine, 3 user-reported bugs | [`problems/rep_bug_squash_mako_3bugs`](problems/rep_bug_squash_mako_3bugs) | 60 min |
| Integration | BikeMap: ride file → maps API → stats, 5 parts | [`problems/int_m2_bikemap`](problems/int_m2_bikemap) | 60 min |

- `problems/` holds the untouched practice copies. This is exactly what the candidate gets.
- `solutions/` is for the interviewer only: the answer keys, reference patches, hidden acceptance
  tests, BikeMap parts 2 to 5, and a grading script. Start with
  [`solutions/README.md`](solutions/README.md).

> **Candidate:** stay out of `solutions/` until both rounds are graded.

---

## 1. Stripe's interview process

Stripe doesn't publish its full loop. What follows comes from Stripe's own engineering
guidance on the Bug Squash round and from many public candidate reports in 2025-2026. Details
vary by team and level, and the recruiter confirms the actual loop.

1. **Recruiter screen** (~30 min): background, motivation, logistics.
2. **Technical phone screen** (~60 min): one practical, multi-part coding problem in your own
   editor and language (parsing, data transformation, a small simulation). Parts get harder as
   you go. Working, readable code matters more than tricky algorithms.
3. **Virtual onsite**, usually 4 to 6 rounds of about 60 minutes each:
   - **Programming / Coding:** another practical, multi-part problem, in the same style as the
     screen.
   - **Bug Squash (a.k.a. Bug Bash):** you get a real, unfamiliar codebase (often an open-source
     library) with failing tests and/or bug reports. You reproduce, localize, fix and verify,
     talking it through with the interviewer. There are often several bugs in unrelated areas.
     Docs and the internet are allowed. AI assistants are reported to be off-limits.
   - **Integration:** you build a feature against an unfamiliar HTTP API, working from its docs,
     inside an existing small codebase. The spec arrives in parts and most people finish about
     three. The usual skills tested are auth, pagination, error handling and retries, data
     transformation, and reading the docs carefully. Internet is allowed, AI is not.
   - **System Design** (mid-level and up): an API or system design discussion, often
     payments-flavored (idempotency, ledgers, webhooks, rate limiting).
   - **Behavioral / Experience** (often with the hiring manager): past projects, ownership,
     collaboration, and Stripe's operating principles.
   - **AI Programming Exercise** (newer, not in every loop): a coding round done *with* an AI
     assistant. It tests how well you steer, review and correct AI output.
4. **Hiring committee / debrief:** each interviewer writes independent feedback with a score.
   The packet is reviewed as a whole, then comes team matching and the offer.

The coding rounds are known for being **practical rather than LeetCode-style**: you're expected
to work in your own environment, with real tooling, in code you didn't write.

## 2. Why these two problems

**Bug Squash → Mako (sqlalchemy/mako, tag `rel_1_3_12`).**
- It's a real, idiomatic open-source codebase: lexer, parse tree, code generator, runtime and
  template lookup, with a 517-test upstream suite. That matches the reports of Stripe using
  real open-source projects rather than toy code.
- It has **three bugs in three unrelated subsystems** (AST regeneration, filesystem lookup,
  control-block codegen), each written up as a user report in `ISSUE.md`. Candidates often
  report "there were three issues", so it also tests prioritization under time pressure.
- The bugs range from a 5-minute fix to a 20-minute one that requires reading generated code.
  That spread separates "systematic debugger" from "got lucky".
- Each fix is 1 to 3 lines. This rewards localizing over rewriting, which is the main lesson
  from candidate post-mortems.

**Integration → BikeMap.**
- This is the **most frequently described Stripe integration problem shape**: read a bike ride
  from a GeoJSON file, call an authenticated map-rendering API and save the image, add
  start/end markers and alternating segment colors, find the nearest landmark to each point
  (paginated API), then compute elapsed time and speed.
- The spec is revealed in 5 parts, like the real round, so you can see how the candidate
  extends their own code under time pressure.
- The **lon/lat trap**, mentioned only in `DOCS.md`, is the classic "did you actually read the
  docs" check. Ride files are `[lon, lat]`, the API wants `[lat, lon]`, and the ride is in
  Amsterdam, so swapped values still look valid and fail silently.
- Later parts add real-world API problems: 5xx and timeouts that need bounded retries (never
  retry 4xx), pagination tokens, malformed records, and bad timestamps.
- It ships with a local mock API (`mock_map/`), so the problem runs fully offline.

## 3. How grading likely works

Stripe interviewers reportedly score each round against a fixed rubric. Each dimension gets a
four-point rating, and the round gets an overall recommendation: **Strong No / No / Yes / Strong
Yes** (no "neutral"). The written evidence matters as much as the score, so note specific
moments ("found bug B in 6 min by walking up the stack trace", "swapped lat/lon in Part 2 and
didn't catch it").

Things Stripe is consistently reported to weigh in these practical rounds:
- **Progress and correctness.** Working code beats clever code. A clean, correct partial
  solution beats a rushed full one ("two of three bugs fixed cleanly and explained well beats
  three rushed changes").
- **Process.** Does the candidate reproduce before changing code, form a hypothesis, test it,
  and confirm the fix?
- **Communication.** Do they narrate their thinking, state assumptions, and react well to hints?
- **Code quality.** Small, well-scoped changes, readable structure, sensible naming, tests
  added for new code.
- **Tooling fluency.** Running a single test, using a debugger or prints, `git diff`, and
  reading tracebacks.

### Scorecard: Bug Squash (Mako)

Rate each 1 (Strong No) to 4 (Strong Yes).

| Dimension | 4: Strong Yes | 2: No |
|---|---|---|
| Reproduction & localization | Runs the failing tests or `ISSUE.md` snippet first, narrows to one test, follows the traceback to the right file quickly | Reads code at random, edits before reproducing |
| Hypothesis-driven debugging | States a hypothesis, picks an experiment to confirm or refute it (pdb, prints, `Template(...).code`) | Trial-and-error edits |
| Fix quality | Minimal, root-cause fix (1-3 lines each), no test edits, explains *why* it's correct | Patches the symptom, broad rewrites, or edits tests |
| Verification | Reruns the targeted test *and* the full suite, maybe adds a regression test | Declares done without running the suite |
| Prioritization | Notices B is quick and does it first, timeboxes C | Sinks 40 min into one bug |
| Communication | Clear running narration, crisp 1-2 sentence summary per fix | Silent or rambling |

Rough anchors: **Strong Yes** = all 3 fixed with clear explanations. **Yes** = 2 fixed cleanly
plus a sound plan for the third. **No** = 1 fixed or fixes not understood. **Strong No** = none,
or tests edited.

### Scorecard: Integration (BikeMap)

| Dimension | 4: Strong Yes | 2: No |
|---|---|---|
| Reading the docs | Inspects the raw data and DOCS first, catches lon/lat, `X-Api-Key`, pagination limits, `Z` timestamps | Codes from SPEC alone, misses the coordinate swap |
| Correctness on edge cases | Handles missing elevation, `null` times, ties, malformed records | Happy path only |
| HTTP / API handling | Auth, binary PNG body written only on 2xx, bounded retries on 5xx/timeouts, no retry on 4xx, full pagination | Retries everything or nothing, ignores status codes |
| Code structure | Small modules or functions, conversion at the boundary, reusable client across parts | One giant function, copy-paste between parts |
| Testing | Adds focused tests, runs the suite often | No tests, never runs the suite |
| Progress | Parts 1-3 solid, or more | Stuck in Part 1 or 2 |
| Communication | Talks through trade-offs, asks clarifying questions | Silent |

Rough anchors: **Strong Yes** = Parts 1-4 correct (including lon/lat), clean code, own tests.
**Yes** = Parts 1-3 correct. **No** = Parts 1-2 with the coordinate swap uncaught, or
untested. **Strong No** = Part 1 incomplete.

The hidden acceptance tests in `solutions/` give you an objective correctness signal per part.
Weigh them alongside the process dimensions above; don't use them alone.

## 4. Running the mock

**You need:** Python 3.11+ (verified on 3.13) and git. Everything else installs from
`requirements.txt`. Both problems run offline after install.

The practice READMEs mention `prep ...` commands and `~/Desktop/Stripe/...` paths. Those belong
to the candidate's local prep tooling, so use the plain commands below instead.

```bash
# Candidate, per round: work on a fresh copy so the original stays untouched
cp -R problems/rep_bug_squash_mako_3bugs ~/attempt-mako && cd ~/attempt-mako
git init -q && git add -A && git commit -qm start      # so `git diff` shows only your changes
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q                                    # Mako: expect 6 failed, 511 passed
```

Same for BikeMap (`problems/int_m2_bikemap`, expect `45 passed`, since Part 1 is new code
rather than failing tests).

**Suggested schedule (~2.5 h):** 5 min setup check → 60 min Bug Squash → 10 min break → 60 min
Integration → 15 min debrief using the scorecards.

**Ground rules to give the candidate:**
- Docs and the internet are fine. No AI assistants (matches reported Stripe rules for these
  rounds).
- Don't edit the existing tests. Adding new tests is encouraged.
- Think out loud. The interviewer may give hints. Taking a hint costs a little, staying stuck
  costs a lot.
- Stop when the timer ends.

For interviewer mechanics (revealing BikeMap parts, hint ladders, grading commands), see
[`solutions/README.md`](solutions/README.md).
