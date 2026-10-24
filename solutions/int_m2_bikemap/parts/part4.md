## Part 4: nearest landmarks

Create `bikemap/landmarks.py` with:

```python
def nearest_landmarks(ride, *, base_url, api_key, timeout=2.0) -> list[dict]:
    ...
```

It fetches **all** landmarks from `GET /v1/landmarks` and, for every track point in
file order, finds the nearest landmark by haversine distance (see "Distances" in
`DOCS.md`). When two landmarks are exactly equally far away, the one with the lower
`id` wins. It returns one dict per point with exactly these keys:

| key | value |
|---|---|
| `point_index` | index of the point in the ride, from 0 (int) |
| `landmark_id` | id of the nearest landmark |
| `landmark_name` | its name |
| `distance_m` | distance in metres rounded to 1 decimal, `round(d, 1)` (float) |

Add a `landmarks` command:

```
python -m bikemap [--base-url URL] [--api-key KEY] landmarks RIDE --out FILE
```

It writes a CSV file (header line first, `\n` line endings) with the columns
`point_index,lat,lon,landmark_id,landmark_name,distance_m`, one row per point in file
order; `lat` and `lon` are the track point's position with 6 decimals, `distance_m`
has 1 decimal. It exits with status 0. Note: Python's `csv.writer` ends rows with `\r\n`
by default; pass `lineterminator="\n"`.

### API errors

- Retry a landmarks request that fails with `500`, `502`, `503` or `504`, or that gets
  no response within `timeout` seconds, making up to **3 attempts** in total and
  waiting at most 0.5 s between attempts. Never retry `4xx` responses. If a page still
  cannot be fetched, raise a `bikemap.errors.BikemapError` subclass (the command exits
  with status 1).
- Skip unusable landmark records. A record is usable when `id` is a non-empty string,
  `name` is a string, and `coordinates` is a list of exactly two numbers forming a
  valid position (see "Conventions" in `DOCS.md`). JSON `true`/`false` are not numbers;
  in Python `bool` is a subclass of `int`, so `isinstance(True, (int, float))` is true and
  needs an explicit `bool` check.

Try it with `python -m mock_map --scenario scenarios/part4.json`.
