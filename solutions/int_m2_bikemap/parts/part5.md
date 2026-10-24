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
