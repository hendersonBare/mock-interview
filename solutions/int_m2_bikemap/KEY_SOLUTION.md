# KEY: int_m2_bikemap

Reference code: `patches/part<k>.patch` (apply to a fresh clone after `python reveal.py <k>`;
part1 needs no reveal); `reference.patch` = `patches/part5.patch`. New modules:
`bikemap/ride.py` (P1), `bikemap/render.py` (P2, P3), `bikemap/mapapi.py` (P3 retry
client, reused in P4), `bikemap/landmarks.py` (P4), `bikemap/stats.py` (P5),
`tests/test_ride_tools.py`; `bikemap/cli.py` gains `summary`, `render [--annotate]`,
`landmarks`, `stats`.

Grade: `~/Desktop/Stripe/keys/grade.sh int_m2_bikemap <part> [workdir]`
(hidden: p1 7, p2 9, p3 10, p4 9, p5 16 -> 51 total). Typical candidate: parts 1-3.

## The trap (DOCS only, not in SPEC)
Ride file positions are GeoJSON `[lon, lat(, ele)]`; every API position (render
`points`, `markers[].at`, landmark `coordinates`) is `[lat, lon]`. The ride is in
Amsterdam (lat ~52.37, lon ~4.89), so swapped values are still in range: the API
silently draws a rotated/mirrored shape at the wrong place (no 400). Hidden tests check
the exact positions the server drew (`MockMapServer.renders[-1]["drawn"]`) and the
`TrackPoint.lat/lon` values. Other DOCS-only details: header `X-Api-Key` (not bearer),
landmarks `limit` max 10 with `page_token`/`next_page_token` (null on last page),
render needs `Content-Type: application/json` (415 otherwise; `bikemap.http.send` with
`json_body` sets it), haversine with R = 6 371 000 m, timestamps must end in `Z`
(`+02:00` is invalid even though `datetime.fromisoformat` accepts it; `parse_utc`
rejects it), some positions lack elevation, `times[i]` may be `null`.

Spec update: the Python-specific behaviors are now stated in the candidate spec parts:
Part 4 (`csv.writer` defaults to `\r\n`; `bool` is an `int` subclass, so JSON booleans
need an explicit check), Part 5 (same `bool` note; `datetime.fromisoformat` accepts
`+02:00`, use `bikemap.timefmt.parse_utc`). Hidden tests are unchanged. The lat/lon trap
is not Python-specific and stays as is.

## Part 1: load_ride + summary
Expected `python -m bikemap summary data/ride_canal_loop.geojson`:
```
name: Canal loop
points: 49
start: 52.379185,4.900061
end: 52.379560,4.899680
bbox: 52.358036,4.877936,52.379560,4.915433
```
Edge cases: 2-value positions (index 4, 13, ...) -> `ele=None`; fractional seconds
(index 7, 31); `null` time -> `None`; bbox from extremes, not endpoints; 6-decimal
formatting of negative longitudes.

## Part 2: render
One POST `/v1/render` with `{"width","height","paths":[{"points":[[lat,lon],...]}]}`, no
color/markers; write `response.body` bytes (binary mode) only after a 2xx; return
`X-Render-Id`. Errors: `ApiError(status)`; do not touch `out_path` on failure. CLI prints
the id, exit 1 on `BikemapError`. First drawn segment for the sample ride:
`[52.379185, 4.900061] -> [52.378791, 4.897311]`, 48 segments, color `#1f77b4`, width 3.

## Part 3: annotate + render retry
Either `paths[0].colors = ["#e4572e", "#2e86ab"]` (documented cycling parameter) or one
path per segment with alternating `color`; markers `[{"at": first, "kind": "start"},
{"at": last, "kind": "end"}]` without colors (defaults `#2a9d8f` / `#e63946`). Retry
500/502/503/504 and transport errors, 3 attempts total, short backoff; 4xx not retried;
still one request when nothing fails. `scenarios/part3.json`: first render 503 once; the
third render call sees two 500s then succeeds.

## Part 4: nearest landmarks
Fetch all pages (`limit<=10`, follow `next_page_token`), parse `coordinates` as
`[lat, lon]`, skip unusable records (not a 2-number list, bools, strings, out of range,
empty id, non-string name), nearest by haversine with tie -> lowest id, compare
unrounded distances, output `round(d, 1)`. Retry 5xx and timeouts (use the `timeout`
argument for each request) up to 3 attempts; 4xx raise immediately. Sample rows:
`0 lm_013 Windmill replica 190.0`, `1 lm_013 120.8`, `3 lm_005 Public fountain 333.3`,
`5 lm_001 Pedestrian bridge 12 410.8`. CSV first data line:
`0,52.379185,4.900061,lm_013,Windmill replica,190.0`.
`scenarios/part4.json`: first landmarks request delayed 3 s (> default 2 s timeout),
the 3rd landmarks request fails 500 once, data has 4 unusable records
(lm_031..lm_034).

## Part 5: ride_stats
Usable point = 2 or 3 numeric values, valid position (after swapping to lat/lon),
`times[i]` present and a valid Z timestamp. Clean ride:
`{"points":49,"used_points":49,"skipped_points":[],"elapsed_s":1251.0,"distance_m":7518.0,
"avg_speed_kmh":21.63,"max_speed_kmh":34.38}`.
`data/ride_rough_signal.geojson`: skipped `[2,4,6,7,9,13,17]` (null time, 1-value
position, string position, `+02:00`, latitude 95, `not-a-time`, missing trailing time),
used 11, elapsed 205.0, distance 1445.0, avg 25.38, max 28.5 (points 10 and 11 share a
timestamp: excluded from max speed, no ZeroDivisionError).

## Edge cases graded
Lat/lon order everywhere; exact bytes saved; no file on error; key from argument/env;
custom size; alternating colors start with the even color; exactly two markers; retry
counts (exactly 3 on persistent 5xx, 1 on 4xx); timeout honoured; tie -> lowest id;
pagination beyond page 2; unusable landmarks/points; zero-dt pair; < 2 usable points.

## Model narration (short)
"Before coding I'll print the first coordinates and a landmarks page: the ride file is
GeoJSON so it's lon,lat, and DOCS says the API is lat,lon everywhere, so I'll convert at
the boundary and keep TrackPoint named fields so the order can't get mixed up again.
Render returns bytes, not JSON, so I write the body in binary and only after a 2xx. For
retries I'll put one small client in front of every call: 5xx and timeouts get up to 3
attempts with a short backoff, 4xx fail fast. Nearest landmark is a linear scan with a
(distance, id) key, which is fine for 30 landmarks x 49 points."
