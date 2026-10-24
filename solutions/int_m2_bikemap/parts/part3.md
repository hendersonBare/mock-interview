## Part 3: annotate the map

Add a keyword argument `annotate=False` to `render_ride` and a `--annotate` flag to
the `render` command. When it is set, the single render request must also:

- color the track segments alternately: segment `k` (from point `k` to point `k+1`,
  counting from 0) is `#e4572e` when `k` is even and `#2e86ab` when `k` is odd,
- add exactly two markers: one of kind `start` at the first point and one of kind
  `end` at the last point, using the API's default marker colors.

Without `annotate` the request is the same as in Part 2.

The renderer is now sometimes busy. Retry a render request that fails with `500`,
`502`, `503` or `504`, or that gets no response, making up to **3 attempts** in total
(the first try plus 2 retries) and waiting at most 0.5 s between attempts. Never retry
`4xx` responses. When every attempt fails, behave as in Part 2 (raise, no file
written; the command exits with status 1).

Try it with `python -m mock_map --scenario scenarios/part3.json`.
