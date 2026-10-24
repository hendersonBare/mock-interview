# Ride maps

<!-- commands -->
> Commands: `pytest -q` runs the tests · `prep grade` when the timer is up · full list in README.md (Quick start).

Riders upload rides recorded on their Trailhead bike computers and want a picture of
the route plus a few facts about it. Pathfinder (see `DOCS.md`) renders maps and knows
about landmarks. Your job is to add the commands that turn a ride file into those
outputs.

The spec has five parts, all listed below. Work through them in order and finish (or
stop) one part before starting the next. Later parts build on earlier ones; interfaces
defined in one part keep working in later parts.

## Part 1: load a ride

Create `bikemap/ride.py` with:

```python
def load_ride(path) -> Ride:
    ...
```

It reads a ride file (format in `DOCS.md`, "Ride files") and returns a
`bikemap.models.Ride` whose `name` is the ride's name and whose `points` are
`bikemap.models.TrackPoint` objects in file order, with:

- `lat`, `lon`: the position in decimal degrees (floats),
- `ele`: the elevation in metres (float) or `None` when the position has none,
- `time`: an aware UTC `datetime`, or `None` when the timestamp is `null`.

Add a `summary` command:

```
python -m bikemap summary data/ride_canal_loop.geojson
```

It prints exactly five lines:

```
name: <name>
points: <number of points>
start: <lat>,<lon>
end: <lat>,<lon>
bbox: <min_lat>,<min_lon>,<max_lat>,<max_lon>
```

`start` is the first point, `end` the last one, and `bbox` the bounding box of all
points. Every coordinate is written with exactly 6 digits after the decimal point
(`52.379185`). `bikemap.cli.main(argv)` must run the same command and return 0.

Example (made-up ride):

```
name: Morning spin
points: 3
start: 51.500000,-0.120000
end: 51.510000,-0.100000
bbox: 51.500000,-0.120000,51.510000,-0.100000
```

## Part 2: render the route

Create `bikemap/render.py` with:

```python
def render_ride(ride, out_path, *, base_url, api_key, width=640, height=480) -> str:
    ...
```

It sends **one** `POST /v1/render` request (see `DOCS.md`) that draws the ride's
track as a single path through all of its points, in file order, using the API's
default color and line width, with no markers, at `width` x `height` pixels. It
writes the response body to `out_path` byte for byte and returns the render id from
the `X-Render-Id` response header.

If the API answers with an error status, raise `bikemap.errors.ApiError` carrying that
status and do not create or overwrite `out_path`. A `bikemap.errors.TransportError`
(no response) may propagate.

Add a `render` command:

```
python -m bikemap [--base-url URL] [--api-key KEY] render RIDE --out FILE [--width W] [--height H]
```

It prints the render id on one line and exits with status 0. On an API or transport
error it prints a message to stderr and exits with status 1. `--base-url` and
`--api-key` default to `BIKEMAP_BASE_URL` / `BIKEMAP_API_KEY`.

Open the PNG you get. Does the map look like the ride?

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

## Part 5: ride statistics

Create `bikemap/stats.py` with:

```python
def ride_stats(path) -> dict:
    ...
```

It reads a ride file and computes statistics from the track points that are
*usable*. Point `i` is usable when

- `coordinates[i]` is a list of 2 or 3 numbers whose first two values form a valid
  position (ride file order, see "Ride files" in `DOCS.md`), and
- `times[i]` exists and is a valid UTC timestamp as described in `DOCS.md`.

"Numbers" excludes JSON `true`/`false` (Python's `bool` is an `int` subclass). Python's
`datetime.fromisoformat` accepts numeric offsets such as `+02:00`, which are not valid
here; `bikemap.timefmt.parse_utc` applies the `DOCS.md` rule.

Real ride files contain glitches (missing time fixes, broken positions); `ride_stats`
must not fail on them. It returns a dict with exactly these keys:

| key | value |
|---|---|
| `points` | number of entries in `coordinates` (int) |
| `used_points` | number of usable points (int) |
| `skipped_points` | indices of the points that are not usable, ascending (list of int) |
| `elapsed_s` | time from the first to the last usable point in seconds, `round(x, 1)` |
| `distance_m` | sum of haversine distances between consecutive usable points (file order), `round(x, 1)` |
| `avg_speed_kmh` | distance divided by elapsed time, in km/h, `round(x, 2)` |
| `max_speed_kmh` | highest speed between two consecutive usable points, in km/h, `round(x, 2)`; pairs whose time difference is not positive are ignored |

Compute speeds from the unrounded distance and time. With fewer than two usable
points (or zero elapsed time) the distance, time and speed values that cannot be
computed are `0.0`.

Add a `stats` command:

```
python -m bikemap stats RIDE
```

It prints the dict as JSON (`json.dumps(result, indent=2, sort_keys=True)`) and exits
with status 0.

`data/ride_rough_signal.geojson` is a ride with glitches.
