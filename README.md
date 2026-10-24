# Stripe mock interview: Bug Squash + Integration

Hey Eland, thanks so much for doing this! I have Stripe's virtual onsite on Tuesday and Wednesday. Tuesday will be Bug Squash + AI programming and Wednesday will be the "Integration" Round. Bug squash consists of running tests from a large repository and fixing those that are failing. I believe there are typically 3 bugs and I think you can pass after fixing just one. Integration is a similar structure, but involves adding/extending features instead of fixing bugs. Throughout our practice, I mostly want to focus on my abilities to communicate and operate under time constraints, as I will have more time TMRW afternoon and Monday to practice the tecnical aspects of the interview. 

There are AI generated notes included for you in the solutions folder. I won't review them because they contain hints and solutions but they should be helpful for you to understand how I am *supposed* to approach/complete the exercises.

| Round | Problem | Folder | Time |
|---|---|---|---|
| Bug Squash | Mako template engine, 3 user-reported bugs | [`problems/rep_bug_squash_mako_3bugs`](problems/rep_bug_squash_mako_3bugs) | 60 min |
| Integration | BikeMap: ride file → maps API → stats, 5 parts | [`problems/int_m2_bikemap`](problems/int_m2_bikemap) | 60 min |

- `problems/` holds the practice copies. This is exactly what the candidate gets. They're
  untouched, except that all 5 BikeMap parts are already in its `SPEC.md`, so you don't need
  to hand them out.
- `solutions/` is for the interviewer only: the answer keys, reference patches, hidden acceptance
  tests, and a grading script. Start with
  [`solutions/README.md`](solutions/README.md).

> **Candidate:** stay out of `solutions/` until both rounds are graded.

---

## 1. Stripe's interview process

1. **Recruiter screen**
2. **Technical team screen** (~60 min): was a multi part coding problem, easy in terms of algorithmic difficulty. completed 3/4 parts and was advanced to VO.
3. **Virtual onsite**, 3 rounds 60 minutes each:
   - **Bug Squash (a.k.a. Bug Bash):** you get a real, unfamiliar codebase (often an open-source
     library) with failing tests and/or bug reports. You reproduce, localize, fix and verify,
     talking it through with the interviewer. There are often several bugs in unrelated areas.
     Docs and the internet are allowed.
   - **Integration:** you build a feature against an unfamiliar HTTP API, working from its docs,
     inside an existing small codebase. The spec arrives in parts and most people finish about
     three. The usual skills tested are auth, pagination, error handling and retries, data
     transformation, and reading the docs carefully. Internet is allowed, AI is not.
   - **AI Programming Exercise** (their first year doing this, new grad candidates only I think): a coding round done *with* an AI assistant. It tests how well you steer, review and correct AI output. Should be pretty easy.
4. **Hiring Manager Chat** deep dive on past projects, ownership,
     collaboration, and Stripe's operating principles.

The coding rounds are known for being **practical rather than LeetCode-style**

## 2. Why these two problems

**Bug Squash → Mako (sqlalchemy/mako, tag `rel_1_3_12`).**
- It's a real, idiomatic open-source codebase: lexer, parse tree, code generator, runtime and
  template lookup, with a 517-test upstream suite. That matches the reports of Stripe using
  real open-source projects rather than toy code.
- It has **three bugs in three unrelated subsystems** (AST regeneration, filesystem lookup,
  control-block codegen), each written up as a user report in `ISSUE.md`. Candidates often
  report "there were three issues", so it also tests prioritization under time pressure.

**Integration → BikeMap.**
- This is the **most frequently described Stripe integration problem shape**: read a bike ride
  from a GeoJSON file, call an authenticated map-rendering API and save the image, add
  start/end markers and alternating segment colors, find the nearest landmark to each point
  (paginated API), then compute elapsed time and speed.
- The spec has 5 parts that build on each other, like the real round, so you can see how the
  candidate extends their own code under time pressure. In the real round each part is revealed
  only after the previous one. Here they're all visible up front, but the candidate should still
  do them in order.
- The **lon/lat trap**, mentioned only in `DOCS.md`, is the classic "did you actually read the
  docs" check. Ride files are `[lon, lat]`, the API wants `[lat, lon]`, and the ride is in
  Amsterdam, so swapped values still look valid and fail silently.
- Later parts add real-world API problems: 5xx and timeouts that need bounded retries (never
  retry 4xx), pagination tokens, malformed records, and bad timestamps.
- It ships with a local mock API (`mock_map/`), so the problem runs fully offline.

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

**Ground rules to give the candidate:**
- Docs and the internet are fine. No AI assistants (matches reported Stripe rules for these
  rounds).
- Don't edit the existing tests. Adding new tests is encouraged.
- Think out loud. The interviewer may give hints. Taking a hint costs a little, staying stuck
  costs a lot.
- Stop when the timer ends.

For interviewer mechanics (hint ladders, grading commands), see
[`solutions/README.md`](solutions/README.md).
